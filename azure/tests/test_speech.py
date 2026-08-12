import sys
from pathlib import Path
from unittest.mock import patch


FUNCTIONS_ROOT = Path(__file__).parents[1] / "src" / "functions"
sys.path.insert(0, str(FUNCTIONS_ROOT))

from ats import speech  # noqa: E402


def test_submit_derives_id_from_self_url(monkeypatch):
    monkeypatch.setenv("SPEECH_ENDPOINT", "https://eastus.api.cognitive.microsoft.com")
    response = {
        "self": "https://eastus.api.cognitive.microsoft.com/speechtotext/transcriptions/job-id?api-version=2025-10-15",
        "displayName": "sample.ogg",
    }

    with patch.object(speech, "_request", return_value=response):
        job = speech.submit("https://example.test/upload/sample.ogg")

    assert job["id"] == "job-id"
