use std::env;
use std::sync::Arc;

use aws_sdk_s3::primitives::ByteStream;
use aws_sdk_transcribe::types::{Settings, TranscriptionJob};
use chrono::{DateTime, Utc};
use lambda_runtime::{Error, LambdaEvent};
use thiserror::Error;
use tracing::{error, info, warn};
use url::Url;

use crate::document::create_document;
use crate::model::{
    JobMetadata, LambdaResponse, ResponseBody, TranscribeEvent, Transcript, TranscriptMode,
};
use crate::transcript::{audio_duration, confidence_stats, create_segments};

#[derive(Debug, Clone)]
pub struct Config {
    pub bucket: String,
    pub max_duration: f64,
    pub confidence_threshold: u8,
    pub document_title: String,
}

impl Config {
    pub fn from_env() -> Result<Self, AppError> {
        let bucket = env::var("BUCKET").map_err(|_| AppError::MissingEnvironment("BUCKET"))?;
        let max_duration = env::var("DOCX_MAX_DURATION")
            .map_err(|_| AppError::MissingEnvironment("DOCX_MAX_DURATION"))?
            .parse()
            .map_err(|_| AppError::InvalidEnvironment("DOCX_MAX_DURATION"))?;
        let confidence_threshold = env::var("CONFIDENCE")
            .unwrap_or_else(|_| "90".to_owned())
            .parse()
            .map_err(|_| AppError::InvalidEnvironment("CONFIDENCE"))?;
        Ok(Self {
            bucket,
            max_duration,
            confidence_threshold,
            document_title: env::var("DOCUMENT_TITLE")
                .unwrap_or_else(|_| "Transcription Results".to_owned()),
        })
    }
}

#[derive(Clone)]
pub struct AppState {
    pub config: Config,
    pub s3: aws_sdk_s3::Client,
    pub transcribe: aws_sdk_transcribe::Client,
    pub http: reqwest::Client,
}

#[derive(Debug, Error)]
pub enum AppError {
    #[error("missing environment variable {0}")]
    MissingEnvironment(&'static str),
    #[error("invalid environment variable {0}")]
    InvalidEnvironment(&'static str),
    #[error("invalid S3 location: {0}")]
    InvalidLocation(String),
    #[error("{0}")]
    Operation(String),
}

#[derive(Debug, Clone, PartialEq)]
enum TranscriptLocation {
    SignedUrl(String),
    S3 { bucket: String, key: String },
}

pub async fn handler(
    event: LambdaEvent<TranscribeEvent>,
    state: Arc<AppState>,
) -> Result<LambdaResponse, Error> {
    let detail = event.payload.detail;
    let job_name = detail.transcription_job_name;
    info!(job = %job_name, "transcribe_to_docx handler started");

    let job = match state
        .transcribe
        .get_transcription_job()
        .transcription_job_name(&job_name)
        .send()
        .await
    {
        Ok(output) => match output.transcription_job {
            Some(job) => job,
            None => {
                return Ok(LambdaResponse::failure(
                    &job_name,
                    "Transcription job failed",
                    format!("Failed to retrieve job details for {job_name}"),
                ));
            }
        },
        Err(source) => {
            error!(job = %job_name, error = %source, "failed to retrieve job details");
            return Ok(LambdaResponse::failure(
                &job_name,
                "Transcription job failed",
                format!("Failed to retrieve job details for {job_name}"),
            ));
        }
    };

    let transcript_uri = match transcript_uri(&job) {
        Ok(uri) => uri,
        Err(source) => {
            error!(job = %job_name, error = %source, "job has no transcript URI");
            return Ok(LambdaResponse::failure(
                &job_name,
                "Transcription job failed",
                format!("Failed to download transcript for {job_name}"),
            ));
        }
    };
    let transcript = match download_transcript(&state, transcript_uri).await {
        Ok(transcript) => transcript,
        Err(source) => {
            error!(job = %job_name, error = %source, "failed to download transcript");
            return Ok(LambdaResponse::failure(
                &job_name,
                "Transcription job failed",
                format!("Failed to download transcript for {job_name}"),
            ));
        }
    };

    let mode = match job.settings().and_then(select_mode) {
        Some(mode) => mode,
        None => {
            let message = format!(
                "Transcribe job name: {job_name}. Channel/speaker/audio mode must be used in this version."
            );
            error!(job = %job_name, "{message}");
            return Ok(LambdaResponse::failure(
                &job_name,
                "Transcription job failed",
                message,
            ));
        }
    };
    let segments = match create_segments(&transcript, mode) {
        Ok(segments) => segments,
        Err(source) => {
            error!(job = %job_name, error = %source, "failed to parse transcript");
            return Ok(LambdaResponse::failure(
                &job_name,
                "Transcription job failed",
                format!("Failed to parse transcript for {job_name}"),
            ));
        }
    };
    let duration = audio_duration(&segments);

    if exceeds_max_duration(duration, state.config.max_duration) {
        let default_message = format!(
            "Job name: {job_name}. Total transcription duration ({duration:.1}s) exceeded DOCX_MAX_DURATION ({}s), download and finish command line using the available JSON.",
            state.config.max_duration
        );
        warn!(job = %job_name, "{default_message}");
        delete_upload_if_completed(&state, &detail.transcription_job_status, &job).await;
        let mut response =
            LambdaResponse::failure(&job_name, "Transcription job stopped", &default_message);
        response.body.lambda = Some(format!(
            "Job name:<br><pre>{job_name}</pre><br>Total transcription duration ({duration:.1}s) exceeded DOCX_MAX_DURATION ({}s), download and finish command line using the available JSON.",
            state.config.max_duration
        ));
        return Ok(response);
    }

    let stats = confidence_stats(&segments);
    let metadata = job_metadata(&job);
    let document = match create_document(
        &transcript,
        &segments,
        &stats,
        &metadata,
        &state.config.document_title,
        state.config.confidence_threshold,
    ) {
        Ok(document) => document,
        Err(source) => {
            error!(job = %job_name, error = %source, "failed to generate DOCX");
            return Ok(LambdaResponse::failure(
                &job_name,
                "Transcription job failed",
                format!("Failed to generate DOCX for {job_name}"),
            ));
        }
    };

    let output_file = format!("{job_name}.docx");
    let key = format!("{}/{}", Utc::now().format("%Y%m%d"), output_file);
    if let Err(source) = state
        .s3
        .put_object()
        .bucket(&state.config.bucket)
        .key(&key)
        .content_type("application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        .body(ByteStream::from(document))
        .send()
        .await
    {
        error!(job = %job_name, error = %source, "failed to upload DOCX");
        return Ok(LambdaResponse::failure(
            &job_name,
            "Transcription job failed",
            format!(
                "Failed to upload file {output_file} to S3 bucket {}",
                state.config.bucket
            ),
        ));
    }

    delete_upload_if_completed(&state, &detail.transcription_job_status, &job).await;

    let s3uri = format!("s3://{}/{key}", state.config.bucket);
    info!(job = %job_name, output = %s3uri, "transcription job completed");
    Ok(LambdaResponse {
        status_code: 200,
        body: ResponseBody {
            job: job_name,
            duration: Some(decimal(duration, 2)),
            languages: Some(metadata.languages),
            confidence: Some(
                stats
                    .average_percent
                    .map_or_else(|| "0.0".to_owned(), |value| decimal(value, 2)),
            ),
            created: Some(metadata.creation_date),
            subject: "Transcription job completed".to_owned(),
            s3uri,
            lambda: None,
            default: None,
        },
    })
}

fn transcript_uri(job: &TranscriptionJob) -> Result<&str, AppError> {
    let transcript = job
        .transcript()
        .ok_or_else(|| AppError::Operation("missing transcript details".to_owned()))?;
    transcript
        .redacted_transcript_file_uri()
        .or_else(|| transcript.transcript_file_uri())
        .ok_or_else(|| AppError::Operation("missing transcript URI".to_owned()))
}

fn select_mode(settings: &Settings) -> Option<TranscriptMode> {
    if settings.channel_identification() == Some(true) {
        Some(TranscriptMode::Channel)
    } else if settings.show_speaker_labels() == Some(true) {
        Some(TranscriptMode::Speaker)
    } else if settings.channel_identification() == Some(false) {
        Some(TranscriptMode::AudioSegments)
    } else {
        None
    }
}

async fn download_transcript(state: &AppState, uri: &str) -> Result<Transcript, AppError> {
    match parse_transcript_location(uri)? {
        TranscriptLocation::SignedUrl(url) => state
            .http
            .get(url)
            .send()
            .await
            .map_err(|source| AppError::Operation(source.to_string()))?
            .error_for_status()
            .map_err(|source| AppError::Operation(source.to_string()))?
            .json()
            .await
            .map_err(|source| AppError::Operation(source.to_string())),
        TranscriptLocation::S3 { bucket, key } => {
            let object = state
                .s3
                .get_object()
                .bucket(bucket)
                .key(key)
                .send()
                .await
                .map_err(|source| AppError::Operation(source.to_string()))?;
            let bytes = object
                .body
                .collect()
                .await
                .map_err(|source| AppError::Operation(source.to_string()))?
                .into_bytes();
            serde_json::from_slice(&bytes).map_err(|source| AppError::Operation(source.to_string()))
        }
    }
}

fn parse_transcript_location(value: &str) -> Result<TranscriptLocation, AppError> {
    let parsed = Url::parse(value).map_err(|_| AppError::InvalidLocation(value.to_owned()))?;
    if parsed.scheme() == "http" || parsed.scheme() == "https" {
        if parsed.query().is_some() {
            return Ok(TranscriptLocation::SignedUrl(value.to_owned()));
        }
        let mut components = parsed.path_segments().ok_or_else(|| {
            AppError::InvalidLocation(format!("URL has no path segments: {value}"))
        })?;
        let bucket = components
            .next()
            .filter(|part| !part.is_empty())
            .ok_or_else(|| AppError::InvalidLocation(format!("URL has no bucket: {value}")))?;
        let key = components.collect::<Vec<_>>().join("/");
        if key.is_empty() {
            return Err(AppError::InvalidLocation(format!(
                "URL has no key: {value}"
            )));
        }
        return Ok(TranscriptLocation::S3 {
            bucket: bucket.to_owned(),
            key,
        });
    }
    if parsed.scheme() == "s3" {
        let bucket = parsed
            .host_str()
            .ok_or_else(|| AppError::InvalidLocation(format!("URI has no bucket: {value}")))?;
        let key = parsed.path().trim_start_matches('/');
        if key.is_empty() {
            return Err(AppError::InvalidLocation(format!(
                "URI has no key: {value}"
            )));
        }
        return Ok(TranscriptLocation::S3 {
            bucket: bucket.to_owned(),
            key: key.to_owned(),
        });
    }
    Err(AppError::InvalidLocation(value.to_owned()))
}

async fn delete_upload_if_completed(state: &AppState, job_status: &str, job: &TranscriptionJob) {
    if job_status != "COMPLETED" {
        return;
    }
    let Some(media_uri) = job.media().and_then(|media| media.media_file_uri()) else {
        warn!("completed job has no media URI to delete");
        return;
    };
    let Ok(TranscriptLocation::S3 { bucket, key }) = parse_transcript_location(media_uri) else {
        warn!(uri = %media_uri, "unable to parse upload media URI");
        return;
    };
    info!(%bucket, %key, "deleting uploaded media");
    if let Err(source) = state
        .s3
        .delete_object()
        .bucket(bucket)
        .key(key)
        .send()
        .await
    {
        warn!(error = %source, "failed to delete uploaded media");
    }
}

fn job_metadata(job: &TranscriptionJob) -> JobMetadata {
    let (language_label, languages) = if let Some(language) = job.language_code() {
        (Some("Language".to_owned()), language.as_str().to_owned())
    } else {
        let languages = job
            .language_codes()
            .iter()
            .filter_map(|item| item.language_code())
            .map(|language| language.as_str())
            .collect::<Vec<_>>()
            .join(", ");
        (
            (!languages.is_empty()).then_some("Language(s)".to_owned()),
            languages,
        )
    };
    let created = job
        .creation_time()
        .and_then(|value| DateTime::<Utc>::from_timestamp(value.secs(), value.subsec_nanos()));
    let settings = job.settings();
    JobMetadata {
        language_label,
        languages,
        media_format: job.media_format().map(|value| value.as_str().to_owned()),
        sample_rate_hz: job.media_sample_rate_hertz(),
        creation_display: created.map(|value| value.format("%a %d %b '%y at %T").to_string()),
        creation_date: created
            .map(|value| value.format("%Y-%m-%d").to_string())
            .unwrap_or_default(),
        redaction_mode: job.content_redaction().map(|redaction| {
            format!(
                "{} [{}]",
                redaction.redaction_type().as_str(),
                redaction.redaction_output().as_str()
            )
        }),
        vocabulary_filter: settings.and_then(|value| {
            Some(format!(
                "{} [{}]",
                value.vocabulary_filter_name()?,
                value.vocabulary_filter_method()?.as_str()
            ))
        }),
        vocabulary: settings
            .and_then(|value| value.vocabulary_name())
            .map(str::to_owned),
    }
}

fn decimal(value: f64, places: usize) -> String {
    let mut value = format!("{value:.places$}");
    if value.contains('.') {
        while value.ends_with('0') {
            value.pop();
        }
        if value.ends_with('.') {
            value.pop();
        }
    }
    value
}

fn exceeds_max_duration(duration: f64, maximum: f64) -> bool {
    duration > maximum
}

#[cfg(test)]
mod tests {
    use aws_sdk_transcribe::types::Settings;
    use serde_json::json;

    use super::*;

    #[test]
    fn parses_supported_s3_locations() {
        assert_eq!(
            parse_transcript_location("s3://bucket-name/key/name.json").unwrap(),
            TranscriptLocation::S3 {
                bucket: "bucket-name".to_owned(),
                key: "key/name.json".to_owned(),
            }
        );
        assert_eq!(
            parse_transcript_location(
                "https://s3.us-east-1.amazonaws.com/bucket-name/key/name.json"
            )
            .unwrap(),
            TranscriptLocation::S3 {
                bucket: "bucket-name".to_owned(),
                key: "key/name.json".to_owned(),
            }
        );
        assert!(matches!(
            parse_transcript_location(
                "https://s3.us-east-1.amazonaws.com/bucket-name/key.json?X-Amz-Signature=value"
            )
            .unwrap(),
            TranscriptLocation::SignedUrl(_)
        ));
    }

    #[test]
    fn preserves_mode_precedence() {
        assert_eq!(
            select_mode(
                &Settings::builder()
                    .channel_identification(true)
                    .show_speaker_labels(true)
                    .build()
            ),
            Some(TranscriptMode::Channel)
        );
        assert_eq!(
            select_mode(&Settings::builder().show_speaker_labels(true).build()),
            Some(TranscriptMode::Speaker)
        );
        assert_eq!(
            select_mode(&Settings::builder().channel_identification(false).build()),
            Some(TranscriptMode::AudioSegments)
        );
        assert_eq!(select_mode(&Settings::builder().build()), None);
    }

    #[test]
    fn response_contract_uses_camel_case_status_code() {
        let response =
            LambdaResponse::failure("example-job", "Transcription job failed", "example failure");
        assert_eq!(
            serde_json::to_value(response).unwrap(),
            json!({
                "statusCode": 500,
                "body": {
                    "job": "example-job",
                    "subject": "Transcription job failed",
                    "s3uri": "N/A",
                    "lambda": "example failure",
                    "default": "example failure"
                }
            })
        );
    }

    #[test]
    fn duration_limit_is_strictly_greater_than() {
        assert!(!exceeds_max_duration(100.0, 100.0));
        assert!(exceeds_max_duration(100.1, 100.0));
    }
}
