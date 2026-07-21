use std::io::Cursor;

use docx_rs::{
    Docx, PageMargin, Paragraph, Run, RunFonts, SectionProperty, SectionType, Shading, Style,
    StyleType, Table, TableCell, TableRow,
};
use thiserror::Error;

use crate::model::{ConfidenceStats, JobMetadata, SpeechSegment, Transcript};
use crate::transcript::{format_speaker_label, format_timestamp};

const A4_WIDTH_TWIPS: u32 = 11_906;
const A4_HEIGHT_TWIPS: u32 = 16_838;
const MARGIN_TWIPS: i32 = 1_083;
const NORMAL_FONT_SIZE: usize = 20;
const ALTERNATE_ROW_COLOUR: &str = "F0F0F0";
const TABLE_STYLE_STANDARD: &str = "LightList";

const CONFIDENCE_LABELS: [&str; 11] = [
    "98% - 100%",
    "90% - 97%",
    "80% - 89%",
    "70% - 79%",
    "60% - 69%",
    "50% - 59%",
    "40% - 49%",
    "30% - 39%",
    "20% - 29%",
    "10% - 19%",
    "0% - 9%",
];

#[derive(Debug, Error)]
pub enum DocumentError {
    #[error("failed to package DOCX: {0}")]
    Package(#[from] zip::result::ZipError),
}

pub fn create_document(
    transcript: &Transcript,
    segments: &[SpeechSegment],
    stats: &ConfidenceStats,
    metadata: &JobMetadata,
    title: &str,
    confidence_threshold: u8,
) -> Result<Vec<u8>, DocumentError> {
    let fonts = calibri_fonts();
    let normal = Style::new("Normal", StyleType::Paragraph)
        .name("Normal")
        .fonts(fonts.clone())
        .size(NORMAL_FONT_SIZE);
    let heading_two = Style::new("Heading2", StyleType::Paragraph)
        .name("heading 2")
        .based_on("Normal")
        .fonts(fonts.clone())
        .size(26)
        .bold();
    let heading_three = Style::new("Heading3", StyleType::Paragraph)
        .name("heading 3")
        .based_on("Normal")
        .fonts(fonts)
        .size(22)
        .bold();

    let mut document = Docx::new()
        .page_size(A4_WIDTH_TWIPS, A4_HEIGHT_TWIPS)
        .page_margin(page_margin())
        .add_style(normal)
        .add_style(heading_two)
        .add_style(heading_three)
        .add_paragraph(heading(title, "Heading2"))
        .add_paragraph(heading("Amazon Transcribe Audio Source", "Heading3"));

    let mut summary_rows = vec![TableRow::new(vec![
        cell("Job Name", None, true),
        cell(&transcript.job_name, None, true),
    ])];
    let mut job_data: Vec<(String, String)> = Vec::new();
    if let Some(last) = segments.last() {
        let duration = last.end_time;
        job_data.push((
            "Audio Duration".to_owned(),
            format!(
                "{}m {}s",
                (duration / 60.0) as u64,
                decimal(duration % 60.0, 2)
            ),
        ));
    }
    let identification = if transcript.results.speaker_labels.is_some() {
        Some("Speaker-separated")
    } else if transcript.results.channel_labels.is_some() {
        Some("Channel-separated")
    } else if transcript.results.audio_segments.is_some() {
        Some("Audio-segments")
    } else {
        None
    };
    if let Some(value) = identification {
        job_data.push(("Audio Identification".to_owned(), value.to_owned()));
    }
    if let Some(label) = &metadata.language_label {
        job_data.push((label.clone(), metadata.languages.clone()));
    }
    if let Some(value) = &metadata.media_format {
        job_data.push(("File Format".to_owned(), value.clone()));
    }
    if let Some(value) = metadata.sample_rate_hz {
        job_data.push(("Sample Rate".to_owned(), format!("{value} Hz")));
    }
    if let Some(value) = &metadata.creation_display {
        job_data.push(("Job Created".to_owned(), value.clone()));
    }
    if let Some(value) = &metadata.redaction_mode {
        job_data.push(("Redaction Mode".to_owned(), value.clone()));
    }
    if let Some(value) = &metadata.vocabulary_filter {
        job_data.push(("Vocabulary Filter".to_owned(), value.clone()));
    }
    if let Some(value) = &metadata.vocabulary {
        job_data.push(("Custom Vocabulary".to_owned(), value.clone()));
    }
    if let Some(value) = stats.average_percent {
        job_data.push((
            "Average Confidence".to_owned(),
            format!("{}%", decimal(value, 2)),
        ));
    }
    summary_rows.extend(job_data.iter().map(|(name, value)| {
        TableRow::new(vec![cell(name, None, false), cell(value, None, false)])
    }));
    document = document
        .add_table(
            Table::new(summary_rows)
                .style(TABLE_STYLE_STANDARD)
                .set_grid(vec![1_950, 2_772]),
        )
        .add_paragraph(Paragraph::new());

    if segments.is_empty() {
        document = document
            .add_paragraph(continuous_section())
            .add_paragraph(heading(
                "This file had no audible speech to transcribe.",
                "Heading3",
            ));
    } else {
        document = document
            .add_paragraph(continuous_section())
            .add_paragraph(heading("Audio Transcription", "Heading3"))
            .add_paragraph(Paragraph::new());

        let high_confidence = Run::new()
            .add_text(format!(
                "WORD CONFIDENCE: >= {confidence_threshold}% in black, "
            ))
            .size(NORMAL_FONT_SIZE)
            .italic()
            .color("000000");
        let low_confidence = Run::new()
            .add_text(format!("< {confidence_threshold}% in yellow highlight"))
            .size(NORMAL_FONT_SIZE)
            .italic()
            .highlight("yellow");
        document = document.add_paragraph(
            Paragraph::new()
                .add_run(high_confidence)
                .add_run(low_confidence),
        );

        for segment in segments {
            let speaker = format_speaker_label(&segment.speaker);
            let prefix = format!("[{}] {}: ", format_timestamp(segment.start_time), speaker);
            let mut paragraph = Paragraph::new().add_run(Run::new().add_text(prefix));
            for word in &segment.words {
                let mut run = Run::new().add_text(&word.text);
                if word.confidence >= f64::from(confidence_threshold) / 100.0 {
                    run = run.color("000000");
                } else {
                    run = run.highlight("yellow");
                }
                if word.confidence == 0.0 {
                    run = run.bold();
                }
                paragraph = paragraph.add_run(run);
            }
            document = document.add_paragraph(paragraph);
        }
        document = document
            .add_paragraph(Paragraph::new())
            .add_paragraph(continuous_section())
            .add_paragraph(heading("Word Confidence Scores", "Heading3"))
            .add_table(confidence_table(stats))
            .add_paragraph(continuous_section());
    }

    let mut output = Cursor::new(Vec::new());
    document.build().pack(&mut output)?;
    Ok(output.into_inner())
}

fn confidence_table(stats: &ConfidenceStats) -> Table {
    let mut rows = vec![TableRow::new(vec![
        cell("Confidence", None, true),
        cell("Count", None, true),
        cell("Percentage", None, true),
    ])];
    for (index, label) in CONFIDENCE_LABELS.iter().enumerate() {
        let shading = (index % 2 == 1).then_some(ALTERNATE_ROW_COLOUR);
        let percentage = stats.bins[index] as f64 / stats.parsed_words as f64 * 100.0;
        rows.push(TableRow::new(vec![
            cell(label, shading, false),
            cell(&stats.bins[index].to_string(), shading, false),
            cell(&format!("{}%", decimal(percentage, 2)), shading, false),
        ]));
    }
    Table::new(rows)
        .style(TABLE_STYLE_STANDARD)
        .set_grid(vec![1_728, 1_152, 1_152])
}

fn heading(text: &str, style: &str) -> Paragraph {
    Paragraph::new()
        .style(style)
        .keep_next(true)
        .widow_control(true)
        .add_run(Run::new().add_text(text))
}

fn cell(text: &str, shading: Option<&str>, bold: bool) -> TableCell {
    let mut run = Run::new().add_text(text);
    if bold {
        run = run.bold();
    }
    let mut cell = TableCell::new().add_paragraph(Paragraph::new().add_run(run));
    if let Some(colour) = shading {
        cell = cell.shading(Shading::new().fill(colour));
    }
    cell
}

fn continuous_section() -> Paragraph {
    Paragraph::new().section_property(SectionProperty {
        page_size: docx_rs::PageSize::new().size(A4_WIDTH_TWIPS, A4_HEIGHT_TWIPS),
        page_margin: page_margin(),
        section_type: Some(SectionType::Continuous),
        ..SectionProperty::default()
    })
}

fn page_margin() -> PageMargin {
    PageMargin {
        top: MARGIN_TWIPS,
        right: MARGIN_TWIPS,
        bottom: MARGIN_TWIPS,
        left: MARGIN_TWIPS,
        header: 720,
        footer: 720,
        gutter: 0,
    }
}

fn calibri_fonts() -> RunFonts {
    RunFonts::new()
        .ascii("Calibri")
        .hi_ansi("Calibri")
        .east_asia("Calibri")
        .cs("Calibri")
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

#[cfg(test)]
mod tests {
    use std::io::{Cursor, Read};

    use zip::ZipArchive;

    use super::*;
    use crate::model::{TranscriptResults, TranscriptWord};

    fn xml_file(bytes: &[u8], name: &str) -> String {
        let mut archive = ZipArchive::new(Cursor::new(bytes)).unwrap();
        let mut contents = String::new();
        archive
            .by_name(name)
            .unwrap()
            .read_to_string(&mut contents)
            .unwrap();
        contents
    }

    #[test]
    fn emits_expected_content_and_formatting() {
        let transcript = Transcript {
            job_name: "example-job".to_owned(),
            results: TranscriptResults {
                speaker_labels: Some(crate::model::SpeakerLabels { segments: vec![] }),
                ..TranscriptResults::default()
            },
        };
        let segments = vec![SpeechSegment {
            start_time: 1.2,
            end_time: 62.25,
            speaker: "spk_0".to_owned(),
            words: vec![
                TranscriptWord {
                    text: "Certain".to_owned(),
                    confidence: 0.99,
                    start_time: 1.2,
                    end_time: 1.5,
                },
                TranscriptWord {
                    text: " uncertain".to_owned(),
                    confidence: 0.5,
                    start_time: 1.6,
                    end_time: 2.0,
                },
            ],
        }];
        let stats = crate::transcript::confidence_stats(&segments);
        let metadata = JobMetadata {
            language_label: Some("Language".to_owned()),
            languages: "en-US".to_owned(),
            creation_date: "2026-07-21".to_owned(),
            ..JobMetadata::default()
        };
        let bytes = create_document(
            &transcript,
            &segments,
            &stats,
            &metadata,
            "Transcription Results",
            90,
        )
        .unwrap();
        let document = xml_file(&bytes, "word/document.xml");
        let styles = xml_file(&bytes, "word/styles.xml");

        assert!(document.contains("Transcription Results"));
        assert!(document.contains("[00:00:01] Speaker 1: "));
        assert!(document.contains(r#"w:highlight w:val="yellow""#));
        assert!(document.contains(r#"w:fill="F0F0F0""#));
        assert!(document.contains(r#"<w:type w:val="continuous""#));
        assert!(document.contains(r#"w:top="1083""#));
        assert!(styles.contains(r#"w:ascii="Calibri""#));
        assert!(styles.contains(r#"w:styleId="Heading2""#));
    }

    #[test]
    fn emits_empty_speech_message_without_confidence_table() {
        let transcript = Transcript {
            job_name: "silent-job".to_owned(),
            results: TranscriptResults::default(),
        };
        let bytes = create_document(
            &transcript,
            &[],
            &ConfidenceStats {
                bins: [0; 11],
                parsed_words: 0,
                average_percent: None,
            },
            &JobMetadata::default(),
            "Transcription Results",
            90,
        )
        .unwrap();
        let document = xml_file(&bytes, "word/document.xml");
        assert!(document.contains("This file had no audible speech to transcribe."));
        assert!(!document.contains("Word Confidence Scores"));
    }
}
