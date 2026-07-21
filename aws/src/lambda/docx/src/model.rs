use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Deserialize)]
pub struct TranscribeEvent {
    pub detail: EventDetail,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(rename_all = "PascalCase")]
pub struct EventDetail {
    pub transcription_job_status: String,
    pub transcription_job_name: String,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
#[serde(rename_all = "camelCase")]
pub struct LambdaResponse {
    pub status_code: u16,
    pub body: ResponseBody,
}

#[derive(Debug, Clone, Default, Serialize, PartialEq)]
pub struct ResponseBody {
    pub job: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub duration: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub languages: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub confidence: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub created: Option<String>,
    pub subject: String,
    pub s3uri: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub lambda: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub default: Option<String>,
}

impl LambdaResponse {
    pub fn failure(
        job: impl Into<String>,
        subject: impl Into<String>,
        message: impl Into<String>,
    ) -> Self {
        let message = message.into();
        Self {
            status_code: 500,
            body: ResponseBody {
                job: job.into(),
                subject: subject.into(),
                s3uri: "N/A".to_owned(),
                lambda: Some(message.clone()),
                default: Some(message),
                ..ResponseBody::default()
            },
        }
    }
}

#[derive(Debug, Clone, Deserialize)]
pub struct Transcript {
    #[serde(rename = "jobName")]
    pub job_name: String,
    pub results: TranscriptResults,
}

#[derive(Debug, Clone, Default, Deserialize)]
pub struct TranscriptResults {
    #[serde(default)]
    pub items: Vec<TranscriptItem>,
    pub speaker_labels: Option<SpeakerLabels>,
    pub channel_labels: Option<ChannelLabels>,
    pub audio_segments: Option<Vec<AudioSegment>>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct SpeakerLabels {
    #[serde(default)]
    pub segments: Vec<SpeakerSegmentInput>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct SpeakerSegmentInput {
    pub start_time: String,
    pub end_time: String,
    pub speaker_label: String,
    #[serde(default)]
    pub items: Vec<TimedItemReference>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct TimedItemReference {
    pub start_time: String,
    pub end_time: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct ChannelLabels {
    #[serde(default)]
    pub channels: Vec<Channel>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct Channel {
    pub channel_label: String,
    #[serde(default)]
    pub items: Vec<TranscriptItem>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct AudioSegment {
    pub start_time: String,
    pub end_time: String,
    #[serde(default)]
    pub transcript: String,
    #[serde(default)]
    pub items: Vec<ItemIndex>,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(untagged)]
pub enum ItemIndex {
    Number(usize),
    String(String),
}

impl ItemIndex {
    pub fn value(&self) -> Option<usize> {
        match self {
            Self::Number(value) => Some(*value),
            Self::String(value) => value.parse().ok(),
        }
    }
}

#[derive(Debug, Clone, Deserialize)]
pub struct TranscriptItem {
    #[serde(rename = "type")]
    pub item_type: String,
    pub start_time: Option<String>,
    pub end_time: Option<String>,
    #[serde(default)]
    pub alternatives: Vec<Alternative>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct Alternative {
    pub content: String,
    pub confidence: Option<String>,
    #[serde(default)]
    pub redactions: Vec<Redaction>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct Redaction {
    pub confidence: String,
}

#[derive(Debug, Clone, PartialEq)]
pub struct SpeechSegment {
    pub start_time: f64,
    pub end_time: f64,
    pub speaker: String,
    pub words: Vec<TranscriptWord>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct TranscriptWord {
    pub text: String,
    pub confidence: f64,
    pub start_time: f64,
    pub end_time: f64,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TranscriptMode {
    Speaker,
    Channel,
    AudioSegments,
}

#[derive(Debug, Clone, PartialEq)]
pub struct ConfidenceStats {
    pub bins: [usize; 11],
    pub parsed_words: usize,
    pub average_percent: Option<f64>,
}

#[derive(Debug, Clone, Default, PartialEq)]
pub struct JobMetadata {
    pub language_label: Option<String>,
    pub languages: String,
    pub media_format: Option<String>,
    pub sample_rate_hz: Option<i32>,
    pub creation_display: Option<String>,
    pub creation_date: String,
    pub redaction_mode: Option<String>,
    pub vocabulary_filter: Option<String>,
    pub vocabulary: Option<String>,
}
