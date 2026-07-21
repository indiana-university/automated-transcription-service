use std::collections::HashMap;

use thiserror::Error;

use crate::model::{
    Alternative, ConfidenceStats, SpeechSegment, Transcript, TranscriptItem, TranscriptMode,
    TranscriptWord,
};

const START_NEW_SEGMENT_DELAY: f64 = 2.0;

#[derive(Debug, Error, PartialEq)]
pub enum TranscriptError {
    #[error("missing {0}")]
    Missing(&'static str),
    #[error("invalid number in {0}: {1}")]
    InvalidNumber(&'static str, String),
    #[error("transcript item has no alternatives")]
    MissingAlternative,
    #[error("audio segment references missing item {0}")]
    InvalidItemIndex(usize),
}

pub fn create_segments(
    transcript: &Transcript,
    mode: TranscriptMode,
) -> Result<Vec<SpeechSegment>, TranscriptError> {
    let mut segments = match mode {
        TranscriptMode::Speaker => create_speaker_segments(transcript)?,
        TranscriptMode::Channel => create_channel_segments(transcript)?,
        TranscriptMode::AudioSegments => create_audio_segments(transcript)?,
    };
    segments.sort_by(|left, right| left.start_time.total_cmp(&right.start_time));
    Ok(segments)
}

fn create_speaker_segments(transcript: &Transcript) -> Result<Vec<SpeechSegment>, TranscriptError> {
    let speaker_labels = transcript
        .results
        .speaker_labels
        .as_ref()
        .ok_or(TranscriptError::Missing("speaker_labels"))?;
    let pronunciation_by_time: HashMap<(&str, &str), (&TranscriptItem, usize)> = transcript
        .results
        .items
        .iter()
        .enumerate()
        .filter(|(_, item)| item.item_type == "pronunciation")
        .filter_map(|(index, item)| {
            Some((
                (item.start_time.as_deref()?, item.end_time.as_deref()?),
                (item, index),
            ))
        })
        .collect();

    let mut output: Vec<SpeechSegment> = Vec::new();
    let mut last_speaker = String::new();
    let mut last_end = 0.0;

    for input in &speaker_labels.segments {
        if input.items.is_empty() {
            continue;
        }
        let start = parse_number("speaker segment start_time", &input.start_time)?;
        let end = parse_number("speaker segment end_time", &input.end_time)?;
        let starts_new = output.is_empty()
            || input.speaker_label != last_speaker
            || start - last_end >= START_NEW_SEGMENT_DELAY;
        if starts_new {
            output.push(SpeechSegment {
                start_time: start,
                end_time: end,
                speaker: input.speaker_label.clone(),
                words: Vec::new(),
            });
        } else if let Some(segment) = output.last_mut() {
            segment.end_time = end;
        }

        let segment = output.last_mut().expect("a segment was just created");
        for reference in &input.items {
            let (item, item_index) = pronunciation_by_time
                .get(&(reference.start_time.as_str(), reference.end_time.as_str()))
                .copied()
                .ok_or(TranscriptError::Missing("matching pronunciation item"))?;
            let (alternative, confidence) = best_alternative(item)?;
            let mut text = if segment.words.is_empty() {
                alternative.content.clone()
            } else {
                format!(" {}", alternative.content)
            };
            if let Some(punctuation) = transcript.results.items.get(item_index + 1)
                && punctuation.item_type == "punctuation"
                && let Some(next) = punctuation.alternatives.first()
            {
                text.push_str(&next.content);
            }
            segment.words.push(TranscriptWord {
                text,
                confidence,
                start_time: parse_number("word start_time", &reference.start_time)?,
                end_time: parse_number("word end_time", &reference.end_time)?,
            });
        }

        last_speaker.clone_from(&input.speaker_label);
        last_end = end;
    }
    Ok(output)
}

fn create_channel_segments(transcript: &Transcript) -> Result<Vec<SpeechSegment>, TranscriptError> {
    let channel_labels = transcript
        .results
        .channel_labels
        .as_ref()
        .ok_or(TranscriptError::Missing("channel_labels"))?;
    let mut output = Vec::new();

    for channel in &channel_labels.channels {
        let mut channel_segments: Vec<SpeechSegment> = Vec::new();
        let mut last_end = 0.0;
        for (index, item) in channel.items.iter().enumerate() {
            if item.item_type != "pronunciation" {
                continue;
            }
            let start_text = item
                .start_time
                .as_deref()
                .ok_or(TranscriptError::Missing("channel item start_time"))?;
            let end_text = item
                .end_time
                .as_deref()
                .ok_or(TranscriptError::Missing("channel item end_time"))?;
            let start = parse_number("channel item start_time", start_text)?;
            let end = parse_number("channel item end_time", end_text)?;
            if channel_segments.is_empty() || start - last_end > 0.1 {
                channel_segments.push(SpeechSegment {
                    start_time: start,
                    end_time: end,
                    speaker: channel.channel_label.clone(),
                    words: Vec::new(),
                });
            } else if let Some(segment) = channel_segments.last_mut() {
                segment.end_time = end;
            }

            let segment = channel_segments
                .last_mut()
                .expect("a channel segment was just created");
            let (alternative, confidence) = best_alternative(item)?;
            let mut text = if segment.words.is_empty() {
                alternative.content.clone()
            } else {
                format!(" {}", alternative.content)
            };
            if let Some(punctuation) = channel.items.get(index + 1)
                && punctuation.item_type == "punctuation"
                && let Some(next) = punctuation.alternatives.first()
            {
                text.push_str(&next.content);
            }
            segment.words.push(TranscriptWord {
                text,
                confidence,
                start_time: start,
                end_time: end,
            });
            last_end = end;
        }
        output.extend(channel_segments);
    }

    output.sort_by(|left, right| left.start_time.total_cmp(&right.start_time));
    Ok(merge_speaker_segments(output))
}

fn create_audio_segments(transcript: &Transcript) -> Result<Vec<SpeechSegment>, TranscriptError> {
    let audio_segments = transcript
        .results
        .audio_segments
        .as_ref()
        .ok_or(TranscriptError::Missing("audio_segments"))?;
    let mut output: Vec<SpeechSegment> = Vec::new();

    for input in audio_segments {
        let mut next = SpeechSegment {
            start_time: parse_number("audio segment start_time", &input.start_time)?,
            end_time: parse_number("audio segment end_time", &input.end_time)?,
            speaker: String::new(),
            words: Vec::new(),
        };
        for item_index in &input.items {
            let index = item_index
                .value()
                .ok_or(TranscriptError::Missing("numeric audio item index"))?;
            let item = transcript
                .results
                .items
                .get(index)
                .ok_or(TranscriptError::InvalidItemIndex(index))?;
            match item.item_type.as_str() {
                "pronunciation" => {
                    let alternative = item
                        .alternatives
                        .first()
                        .ok_or(TranscriptError::MissingAlternative)?;
                    let confidence = alternative_confidence(alternative)?;
                    let mut text = alternative.content.clone();
                    if !next.words.is_empty() {
                        text.insert(0, ' ');
                    }
                    next.words.push(TranscriptWord {
                        text,
                        confidence,
                        start_time: parse_optional_number(
                            "audio item start_time",
                            &item.start_time,
                        )?,
                        end_time: parse_optional_number("audio item end_time", &item.end_time)?,
                    });
                }
                "punctuation" => {
                    if let (Some(word), Some(alternative)) =
                        (next.words.last_mut(), item.alternatives.first())
                    {
                        word.text.push_str(&alternative.content);
                    }
                }
                _ => {}
            }
        }

        if let Some(previous) = output.last_mut()
            && next.start_time - previous.end_time < START_NEW_SEGMENT_DELAY
        {
            previous.end_time = next.end_time;
            previous.words.extend(next.words);
        } else {
            output.push(next);
        }
    }
    Ok(output)
}

fn merge_speaker_segments(input: Vec<SpeechSegment>) -> Vec<SpeechSegment> {
    let mut output: Vec<SpeechSegment> = Vec::new();
    for mut segment in input {
        if let Some(previous) = output.last_mut()
            && segment.speaker == previous.speaker
            && segment.start_time - previous.end_time < START_NEW_SEGMENT_DELAY
        {
            previous.end_time = segment.end_time;
            if let Some(first_word) = segment.words.first_mut() {
                first_word.text.insert(0, ' ');
            }
            previous.words.extend(segment.words);
        } else {
            output.push(segment);
        }
    }
    output
}

fn best_alternative(item: &TranscriptItem) -> Result<(&Alternative, f64), TranscriptError> {
    let alternative = item
        .alternatives
        .iter()
        .max_by(|left, right| confidence_for_order(left).total_cmp(&confidence_for_order(right)))
        .ok_or(TranscriptError::MissingAlternative)?;
    Ok((alternative, alternative_confidence(alternative)?))
}

fn confidence_for_order(alternative: &Alternative) -> f64 {
    alternative
        .confidence
        .as_deref()
        .and_then(|value| value.parse().ok())
        .or_else(|| {
            alternative
                .redactions
                .first()
                .and_then(|value| value.confidence.parse().ok())
        })
        .unwrap_or(-1.0)
}

fn alternative_confidence(alternative: &Alternative) -> Result<f64, TranscriptError> {
    if let Some(value) = &alternative.confidence {
        return parse_number("confidence", value);
    }
    let value = alternative
        .redactions
        .first()
        .ok_or(TranscriptError::Missing(
            "confidence or redaction confidence",
        ))?;
    parse_number("redaction confidence", &value.confidence)
}

fn parse_optional_number(
    field: &'static str,
    value: &Option<String>,
) -> Result<f64, TranscriptError> {
    parse_number(
        field,
        value.as_deref().ok_or(TranscriptError::Missing(field))?,
    )
}

fn parse_number(field: &'static str, value: &str) -> Result<f64, TranscriptError> {
    value
        .parse()
        .map_err(|_| TranscriptError::InvalidNumber(field, value.to_owned()))
}

pub fn confidence_stats(segments: &[SpeechSegment]) -> ConfidenceStats {
    let mut bins = [0; 11];
    let mut total_percent = 0.0;
    let mut parsed_words = 0;
    for word in segments.iter().flat_map(|segment| &segment.words) {
        let index = if word.confidence >= 0.98 {
            0
        } else if word.confidence >= 0.9 {
            1
        } else {
            (10 - (word.confidence * 10.0).floor() as usize).min(10)
        };
        bins[index] += 1;
        total_percent += word.confidence * 100.0;
        parsed_words += 1;
    }
    ConfidenceStats {
        bins,
        parsed_words,
        average_percent: (parsed_words > 0).then_some(total_percent / parsed_words as f64),
    }
}

pub fn audio_duration(segments: &[SpeechSegment]) -> f64 {
    segments.last().map_or(0.0, |segment| segment.end_time)
}

pub fn format_speaker_label(label: &str) -> String {
    if let Some(index) = label.strip_prefix("spk_")
        && let Ok(index) = index.parse::<usize>()
    {
        return format!("Speaker {}", index + 1);
    }
    label.to_owned()
}

pub fn format_timestamp(seconds: f64) -> String {
    let seconds = seconds.max(0.0).floor() as u64;
    format!(
        "{:02}:{:02}:{:02}",
        seconds / 3600,
        (seconds % 3600) / 60,
        seconds % 60
    )
}

#[cfg(test)]
mod tests {
    use pretty_assertions::assert_eq;
    use serde_json::json;

    use super::*;

    fn transcript(value: serde_json::Value) -> Transcript {
        serde_json::from_value(value).unwrap()
    }

    #[test]
    fn formats_timestamps_and_speakers() {
        assert_eq!(format_timestamp(0.0), "00:00:00");
        assert_eq!(format_timestamp(10_000.9), "02:46:40");
        assert_eq!(format_speaker_label("spk_0"), "Speaker 1");
        assert_eq!(format_speaker_label("spk_1"), "Speaker 2");
        assert_eq!(format_speaker_label("Mr. Jones"), "Mr. Jones");
    }

    #[test]
    fn parses_speaker_segments_and_punctuation() {
        let input = transcript(json!({
            "jobName": "speaker-job",
            "results": {
                "items": [
                    {"type":"pronunciation","start_time":"0.0","end_time":"0.4","alternatives":[{"content":"Hello","confidence":"0.99"}]},
                    {"type":"punctuation","alternatives":[{"content":","}]},
                    {"type":"pronunciation","start_time":"0.5","end_time":"0.9","alternatives":[{"content":"world","confidence":"0.75"}]}
                ],
                "speaker_labels": {"segments":[
                    {"start_time":"0.0","end_time":"0.9","speaker_label":"spk_0","items":[
                        {"start_time":"0.0","end_time":"0.4"},
                        {"start_time":"0.5","end_time":"0.9"}
                    ]}
                ]}
            }
        }));
        let segments = create_segments(&input, TranscriptMode::Speaker).unwrap();
        assert_eq!(segments.len(), 1);
        assert_eq!(segments[0].words[0].text, "Hello,");
        assert_eq!(segments[0].words[1].text, " world");
        assert_eq!(confidence_stats(&segments).bins[0], 1);
        assert_eq!(confidence_stats(&segments).bins[3], 1);
    }

    #[test]
    fn sorts_channels_and_merges_close_turns() {
        let input = transcript(json!({
            "jobName": "channel-job",
            "results": {"items":[], "channel_labels":{"channels":[
                {"channel_label":"ch_1","items":[
                    {"type":"pronunciation","start_time":"2.0","end_time":"2.2","alternatives":[{"content":"late","confidence":"0.9"}]}
                ]},
                {"channel_label":"ch_0","items":[
                    {"type":"pronunciation","start_time":"0.0","end_time":"0.2","alternatives":[{"content":"first","confidence":"0.9"}]},
                    {"type":"pronunciation","start_time":"0.25","end_time":"0.4","alternatives":[{"content":"again","confidence":"0.9"}]}
                ]}
            ]}}
        }));
        let segments = create_segments(&input, TranscriptMode::Channel).unwrap();
        assert_eq!(segments.len(), 2);
        assert_eq!(segments[0].speaker, "ch_0");
        assert_eq!(segments[0].words[1].text, " again");
        assert_eq!(segments[1].speaker, "ch_1");
    }

    #[test]
    fn parses_audio_segments_with_numeric_and_string_indexes() {
        let input = transcript(json!({
            "jobName":"audio-job",
            "results": {
                "items":[
                    {"type":"pronunciation","start_time":"0.0","end_time":"0.2","alternatives":[{"content":"One","confidence":"0.9"}]},
                    {"type":"punctuation","alternatives":[{"content":"."}]},
                    {"type":"pronunciation","start_time":"0.5","end_time":"0.8","alternatives":[{"content":"Two","confidence":"0.8"}]}
                ],
                "audio_segments":[
                    {"start_time":"0.0","end_time":"0.2","transcript":"One.","items":[0,1]},
                    {"start_time":"0.5","end_time":"0.8","transcript":"Two","items":["2"]}
                ]
            }
        }));
        let segments = create_segments(&input, TranscriptMode::AudioSegments).unwrap();
        assert_eq!(segments.len(), 1);
        assert_eq!(segments[0].words[0].text, "One.");
        assert_eq!(segments[0].words[1].text, "Two");
        assert_eq!(audio_duration(&segments), 0.8);
    }

    #[test]
    fn starts_a_new_segment_at_two_seconds() {
        let input = transcript(json!({
            "jobName":"audio-job",
            "results": {
                "items":[
                    {"type":"pronunciation","start_time":"0","end_time":"1","alternatives":[{"content":"One","confidence":"1"}]},
                    {"type":"pronunciation","start_time":"3","end_time":"4","alternatives":[{"content":"Two","confidence":"1"}]}
                ],
                "audio_segments":[
                    {"start_time":"0","end_time":"1","items":[0]},
                    {"start_time":"3","end_time":"4","items":[1]}
                ]
            }
        }));
        let segments = create_segments(&input, TranscriptMode::AudioSegments).unwrap();
        assert_eq!(segments.len(), 2);
    }

    #[test]
    fn reads_redacted_confidence_when_standard_confidence_is_absent() {
        let input = transcript(json!({
            "jobName": "redacted-job",
            "results": {
                "items": [
                    {
                        "type": "pronunciation",
                        "start_time": "0",
                        "end_time": "1",
                        "alternatives": [{
                            "content": "[PII]",
                            "redactions": [{"confidence": "0.42"}]
                        }]
                    }
                ],
                "speaker_labels": {"segments": [{
                    "start_time": "0",
                    "end_time": "1",
                    "speaker_label": "spk_0",
                    "items": [{"start_time": "0", "end_time": "1"}]
                }]}
            }
        }));
        let segments = create_segments(&input, TranscriptMode::Speaker).unwrap();
        assert_eq!(segments[0].words[0].confidence, 0.42);
    }
}
