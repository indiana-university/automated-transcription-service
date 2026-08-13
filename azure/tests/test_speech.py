import sys
from pathlib import Path
from unittest.mock import Mock, patch


FUNCTIONS_ROOT = Path(__file__).parents[1] / "src" / "functions"
sys.path.insert(0, str(FUNCTIONS_ROOT))

from ats import speech  # noqa: E402


def test_job_name_uses_eight_digit_random_suffix_and_sanitizes_filename():
    with patch.object(speech.secrets, "randbelow", return_value=48372615) as randbelow:
        name = speech.job_name("https://example.test/upload/My%20Sample.ogg")

    assert name == "My_Sample.ogg-48372615"
    randbelow.assert_called_once_with(100_000_000)


def test_job_name_zero_pads_suffix():
    with patch.object(speech.secrets, "randbelow", return_value=42):
        name = speech.job_name("https://example.test/upload/sample.ogg")

    assert name == "sample.ogg-00000042"


def test_submit_derives_id_from_self_url_and_preserves_unique_name(monkeypatch):
    monkeypatch.setenv("SPEECH_ENDPOINT", "https://eastus.api.cognitive.microsoft.com")
    response = {
        "self": "https://eastus.api.cognitive.microsoft.com/speechtotext/transcriptions/job-id?api-version=2025-10-15",
        "displayName": "service-value",
    }
    request = Mock(return_value=response)

    with patch.object(speech, "_request", request):
        job = speech.submit(
            "https://example.test/upload/sample.ogg",
            "sample.ogg-48372615",
            "instance-id",
        )

    assert job["id"] == "job-id"
    assert job["displayName"] == "sample.ogg-48372615"
    assert request.call_args.args[2]["displayName"] == job["displayName"]
    assert job["customProperties"] == {"durableInstanceId": "instance-id"}


def test_register_webhook_replaces_existing_registration(monkeypatch):
    monkeypatch.setenv("SPEECH_ENDPOINT", "https://speech.test")
    existing = {
        "values": [{
            "displayName": "ATS transcription completion",
            "self": "https://speech.test/speechtotext/v3.2/webhooks/hook-id",
        }]
    }
    created = {"status": "Succeeded", "webUrl": "https://function.test/webhook"}
    request = Mock(side_effect=[existing, {}, created])

    with patch.object(speech, "_request", request):
        result = speech.register_webhook("https://function.test/webhook", "secret")

    assert result == created
    assert request.call_args_list[1].args[:2] == (
        "DELETE",
        "https://speech.test/speechtotext/v3.2/webhooks/hook-id",
    )
    payload = request.call_args_list[2].args[2]
    assert payload["events"] == {"transcriptionCompletion": True}
    assert payload["properties"] == {"secret": "secret"}


def test_register_webhook_keeps_healthy_registration(monkeypatch):
    monkeypatch.setenv("SPEECH_ENDPOINT", "https://speech.test")
    existing = {
        "displayName": "ATS transcription completion",
        "status": "Succeeded",
        "webUrl": "https://function.test/webhook",
    }
    request = Mock(return_value={"values": [existing]})

    with patch.object(speech, "_request", request):
        result = speech.register_webhook("https://function.test/webhook", "secret")

    assert result == existing
    request.assert_called_once()
