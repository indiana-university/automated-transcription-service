import statistics
from datetime import timedelta
from io import BytesIO

from docx import Document
from docx.enum.text import WD_COLOR_INDEX
from docx.shared import Mm, Pt


def _seconds(ticks):
    return float(ticks or 0) / 10_000_000


def _timestamp(ticks):
    value = timedelta(seconds=_seconds(ticks))
    total = int(value.total_seconds())
    return f"{total // 3600:02d}:{(total % 3600) // 60:02d}:{total % 60:02d}"


def transcript_summary(data):
    phrases = [item for item in data.get("recognizedPhrases", []) if item.get("recognitionStatus") == "Success"]
    confidences = [item["nBest"][0].get("confidence", 0) for item in phrases if item.get("nBest")]
    languages = sorted({item["locale"] for item in phrases if item.get("locale")})
    return {
        "confidence": round(statistics.mean(confidences) * 100, 2) if confidences else 0,
        "duration": round(_seconds(data.get("durationInTicks")), 2),
        "languages": ", ".join(languages),
        "phrases": len(phrases),
    }


def create_docx(data, job_name, title="Transcription Results", threshold=90):
    document = Document()
    section = document.sections[0]
    section.left_margin = section.right_margin = Mm(19.1)
    section.top_margin = section.bottom_margin = Mm(19.1)
    document.styles["Normal"].font.size = Pt(10)
    document.add_heading(title, 1)

    summary = transcript_summary(data)
    table = document.add_table(rows=0, cols=2)
    table.style = "Light List"
    for label, value in (
        ("Job Name", job_name),
        ("Audio Duration", f"{summary['duration']} seconds"),
        ("Language(s)", summary["languages"] or "Not reported"),
        ("Average Confidence", f"{summary['confidence']}%"),
    ):
        cells = table.add_row().cells
        cells[0].text, cells[1].text = label, str(value)

    document.add_heading("Transcript", 2)
    for phrase in data.get("recognizedPhrases", []):
        if phrase.get("recognitionStatus") != "Success" or not phrase.get("nBest"):
            continue
        best = phrase["nBest"][0]
        speaker = phrase.get("speaker")
        label = f"Speaker {int(speaker) + 1}" if speaker is not None else f"Channel {phrase.get('channel', 0) + 1}"
        paragraph = document.add_paragraph()
        paragraph.add_run(f"[{_timestamp(phrase.get('offsetInTicks'))}] {label}: ").bold = True
        run = paragraph.add_run(best.get("display") or best.get("lexical", ""))
        if float(best.get("confidence", 0)) * 100 < threshold:
            run.font.highlight_color = WD_COLOR_INDEX.YELLOW

    output = BytesIO()
    document.save(output)
    return output.getvalue(), summary
