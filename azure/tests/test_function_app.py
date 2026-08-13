import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch


FUNCTIONS_ROOT = Path(__file__).parents[1] / "src" / "functions"
sys.path.insert(0, str(FUNCTIONS_ROOT))

from function_app import start_from_upload as start_from_upload_builder  # noqa: E402
from function_app import speech_webhook as speech_webhook_builder  # noqa: E402
from function_app import transcription_orchestrator as orchestrator_builder  # noqa: E402


class MissingOrchestrationStatus:
    def __bool__(self):
        return False


def test_start_from_upload_starts_missing_orchestration():
    event = {
        "id": "12345678-1234-5678-9abc-123456789abc",
        "data": {"url": "https://example.test/upload/sample.ogg"},
    }
    message = SimpleNamespace(get_body=lambda: json.dumps(event).encode())
    client = SimpleNamespace(
        get_status=AsyncMock(return_value=MissingOrchestrationStatus()),
        start_new=AsyncMock(),
    )

    start_from_upload = start_from_upload_builder._function.get_user_function().__wrapped__
    with patch("function_app.speech.job_name", return_value="sample.ogg-48372615"):
        asyncio.run(start_from_upload(message, client))

    client.start_new.assert_awaited_once_with(
        "transcription_orchestrator",
        "12345678-1234-5678-9abc-123456789abc",
        {
            "blob_url": "https://example.test/upload/sample.ogg",
            "instance_id": "12345678-1234-5678-9abc-123456789abc",
            "job_name": "sample.ogg-48372615",
        },
    )


def test_orchestrator_does_not_submit_rejected_audio():
    source = {
        "blob_url": "https://example.test/upload/stereo.wav",
        "job_name": "stereo.wav-unique",
    }
    context = SimpleNamespace(
        get_input=Mock(return_value=source),
        call_activity=Mock(side_effect=lambda name, value: (name, value)),
    )
    orchestrator = (
        orchestrator_builder._function.get_user_function().__closure__[0].cell_contents
    )
    workflow = orchestrator(context)

    assert next(workflow) == ("validate_audio", source)
    notification = workflow.send({"valid": False, "reason": "Stereo is invalid."})

    assert notification[0] == "send_notification"
    assert notification[1]["reason"] == "Stereo is invalid."
    try:
        workflow.send(None)
    except StopIteration as completed:
        assert completed.value["subject"] == "Transcription rejected"
    else:
        raise AssertionError("Rejected orchestration did not complete")
    assert not any(
        call.args[0] == "submit_transcription"
        for call in context.call_activity.call_args_list
    )


def test_orchestrator_deletes_upload_when_speech_succeeds():
    source = {
        "blob_url": "https://example.test/upload/sample.ogg",
        "instance_id": "instance-id",
        "job_name": "sample.ogg-unique",
    }
    completion = SimpleNamespace()
    context = SimpleNamespace(
        get_input=Mock(return_value=source),
        call_activity=Mock(side_effect=lambda name, value: (name, value)),
        wait_for_external_event=Mock(return_value=completion),
    )
    orchestrator = (
        orchestrator_builder._function.get_user_function().__closure__[0].cell_contents
    )
    workflow = orchestrator(context)

    assert next(workflow) == ("validate_audio", source)
    assert workflow.send({"valid": True}) == ("ensure_speech_webhook", None)
    assert workflow.send(None) == ("submit_transcription", source)
    job = {"id": "job-id", "displayName": "sample.ogg"}
    assert workflow.send(job) is completion
    assert workflow.send('{"status":"Succeeded","error":null}') == (
        "delete_upload",
        source,
    )
    assert workflow.send(None) == ("finish_transcription", job)
    result = {"job": "sample.ogg", "url": "https://example.test/download/sample.ogg.docx"}
    notification = workflow.send(result)
    assert notification[0] == "send_notification"
    assert notification[1]["subject"] == "Transcription job completed"
    try:
        workflow.send(None)
    except StopIteration as completed:
        assert completed.value == result
    else:
        raise AssertionError("Successful orchestration did not complete")


def test_orchestrator_reports_failed_webhook_status():
    source = {
        "blob_url": "https://example.test/upload/sample.ogg",
        "instance_id": "instance-id",
        "job_name": "sample.ogg-unique",
    }
    completion = SimpleNamespace()
    context = SimpleNamespace(
        get_input=Mock(return_value=source),
        call_activity=Mock(side_effect=lambda name, value: (name, value)),
        wait_for_external_event=Mock(return_value=completion),
    )
    orchestrator = (
        orchestrator_builder._function.get_user_function().__closure__[0].cell_contents
    )
    workflow = orchestrator(context)

    assert next(workflow) == ("validate_audio", source)
    assert workflow.send({"valid": True}) == ("ensure_speech_webhook", None)
    assert workflow.send(None) == ("submit_transcription", source)
    job = {"id": "job-id", "displayName": "sample.ogg"}
    assert workflow.send(job) is completion
    assert workflow.send(
        {"status": "Failed", "error": {"message": "Invalid audio"}}
    ) == (
        "send_notification",
        {
            "subject": "Transcription job failed",
            "job": "sample.ogg",
            "url": "N/A",
            "reason": "Invalid audio",
        },
    )


def test_speech_webhook_echoes_validation_token():
    request = SimpleNamespace(params={"validationToken": "challenge-token"})
    client = SimpleNamespace(raise_event=AsyncMock())
    webhook = speech_webhook_builder._function.get_user_function().__wrapped__

    response = asyncio.run(webhook(request, client))

    assert response.status_code == 200
    assert response.get_body() == b"challenge-token"
    client.raise_event.assert_not_awaited()


def test_speech_webhook_verifies_and_raises_terminal_event():
    content = json.dumps({"self": "https://speech.test/transcriptions/job-id"}).encode()
    request = SimpleNamespace(
        params={},
        headers={"X-MicrosoftSpeechServices-Signature": "signature"},
        get_body=lambda: content,
    )
    client = SimpleNamespace(raise_event=AsyncMock())
    webhook = speech_webhook_builder._function.get_user_function().__wrapped__
    job = {
        "status": "Succeeded",
        "customProperties": {"durableInstanceId": "instance-id"},
    }

    with (
        patch("function_app.webhooks.valid_signature", return_value=True),
        patch("function_app.speech.status", return_value=job),
    ):
        response = asyncio.run(webhook(request, client))

    assert response.status_code == 202
    client.raise_event.assert_awaited_once_with(
        "instance-id", "speech_status", {"status": "Succeeded", "error": None}
    )
