import json
import os
from datetime import timedelta

import azure.durable_functions as df
import azure.functions as func
from ats import audio, documents, notifications, speech, storage

app = df.DFApp(http_auth_level=func.AuthLevel.FUNCTION)


@app.function_name(name="start_from_upload")
@app.queue_trigger(
    arg_name="message",
    queue_name="audio-to-transcribe",
    connection="EVENT_QUEUE_CONNECTION",
)
@app.durable_client_input(client_name="client")
async def start_from_upload(message: func.QueueMessage, client):
    event = json.loads(message.get_body().decode("utf-8"))
    instance_id = event["id"]
    if not await client.get_status(instance_id):
        await client.start_new(
            "transcription_orchestrator",
            instance_id,
            {"blob_url": event["data"]["url"]},
        )


@app.orchestration_trigger(context_name="context")
def transcription_orchestrator(context: df.DurableOrchestrationContext):
    source = context.get_input()
    validation = yield context.call_activity("validate_audio", source)
    if not validation["valid"]:
        rejection = {
            "subject": "Transcription rejected",
            "job": source["blob_url"].rsplit("/", 1)[-1],
            "url": "N/A",
            "reason": validation["reason"],
        }
        yield context.call_activity("send_notification", rejection)
        return rejection
    job = yield context.call_activity("submit_transcription", source)
    deadline = context.current_utc_datetime + timedelta(hours=25)
    while context.current_utc_datetime < deadline:
        state = yield context.call_activity("get_transcription_status", job)
        if state == "Succeeded":
            result = yield context.call_activity("finish_transcription", job)
            yield context.call_activity(
                "send_notification",
                {"subject": "Transcription job completed", **result},
            )
            return result
        if state == "Failed":
            failure = {
                "subject": "Transcription job failed",
                "job": job["displayName"],
                "url": "N/A",
            }
            yield context.call_activity("send_notification", failure)
            return failure
        wake_at = context.current_utc_datetime + timedelta(
            minutes=int(os.environ.get("POLL_INTERVAL_MINUTES", "10"))
        )
        yield context.create_timer(wake_at)
    timeout = {
        "subject": "Transcription job timed out",
        "job": job["displayName"],
        "url": "N/A",
    }
    yield context.call_activity("send_notification", timeout)
    return timeout


@app.activity_trigger(input_name="source")
def validate_audio(source):
    return audio.validate(source["blob_url"])


@app.activity_trigger(input_name="source")
def submit_transcription(source):
    return speech.submit(source["blob_url"])


@app.activity_trigger(input_name="job")
def get_transcription_status(job):
    return speech.status(job)["status"]


@app.activity_trigger(input_name="job")
def finish_transcription(job):
    data = speech.result(job)
    name = job["displayName"]
    content, summary = documents.create_docx(
        data,
        name,
        os.environ.get("DOCUMENT_TITLE", "Transcription Results"),
        int(os.environ.get("CONFIDENCE", "90")),
        job.get("locale"),
    )
    url = storage.save_document(name, content)
    storage.record_job(name, summary, url)
    return {"job": name, "url": url, **summary}


@app.activity_trigger(input_name="message")
def send_notification(message):
    notifications.send(message)


@app.route(route="reports/export", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
def export_report(req: func.HttpRequest):
    return func.HttpResponse(
        json.dumps(storage.export_jobs()), mimetype="application/json"
    )
