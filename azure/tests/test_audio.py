from io import BytesIO
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import wave


FUNCTIONS_ROOT = Path(__file__).parents[1] / "src" / "functions"
sys.path.insert(0, str(FUNCTIONS_ROOT))

from ats.audio import inspect_header  # noqa: E402


def wave_content(channels):
    content = BytesIO()
    with wave.open(content, "wb") as audio:
        audio.setnchannels(channels)
        audio.setsampwidth(2)
        audio.setframerate(16_000)
        audio.writeframes(b"\x00\x00" * channels * 160)
    return content.getvalue()


def test_accepts_mono_audio():
    content = wave_content(1)

    result = inspect_header("sample.wav", content, len(content))

    assert result == {
        "valid": True,
        "channels": 1,
        "format": "wav",
        "sample_rate": 16_000,
    }


def test_rejects_stereo_audio_before_speech():
    content = wave_content(2)

    result = inspect_header("sample.wav", content, len(content))

    assert result["valid"] is False
    assert result["reason"] == (
        "Speaker diarization requires mono audio; this file has 2 channels."
    )


def test_accepts_mono_mp4():
    metadata = SimpleNamespace(channels=1, samplerate=32_000)

    with patch("ats.audio.TinyTag.get", return_value=metadata) as get_metadata:
        result = inspect_header("recording.mp4", b"mp4 content", 11)

    assert result == {
        "valid": True,
        "channels": 1,
        "format": "mp4",
        "sample_rate": 32_000,
    }
    get_metadata.assert_called_once()


def test_rejects_unverifiable_format():
    result = inspect_header("sample.webm", b"not audio", 9)

    assert result["valid"] is False
    assert "Unsupported or unverifiable" in result["reason"]
