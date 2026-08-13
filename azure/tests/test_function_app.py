import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch


FUNCTIONS_ROOT = Path(__file__).parents[1] / "src" / "functions"
sys.path.insert(0, str(FUNCTIONS_ROOT))

from function_app import start_from_upload as start_from_upload_builder  # noqa: E402
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
        "job_name": "sample.ogg-unique",
    }
    context = SimpleNamespace(
        current_utc_datetime=datetime(2026, 8, 13, tzinfo=timezone.utc),
        get_input=Mock(return_value=source),
        call_activity=Mock(side_effect=lambda name, value: (name, value)),
    )
    orchestrator = (
        orchestrator_builder._function.get_user_function().__closure__[0].cell_contents
    )
    workflow = orchestrator(context)

    assert next(workflow) == ("validate_audio", source)
    assert workflow.send({"valid": True}) == ("submit_transcription", source)
    job = {"id": "job-id", "displayName": "sample.ogg"}
    assert workflow.send(job) == ("get_transcription_status", job)
    assert workflow.send("Succeeded") == ("delete_upload", source)
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
