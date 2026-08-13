import json
import os

import azure.durable_functions as df
import azure.functions as func
from ats import audio, documents, notifications, speech, storage, webhooks

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
    blob_url = event["data"]["url"]
    if not await client.get_status(instance_id):
        await client.start_new(
            "transcription_orchestrator",
            instance_id,
            {
                "blob_url": blob_url,
                "instance_id": instance_id,
                "job_name": speech.job_name(blob_url),
            },
        )


@app.orchestration_trigger(context_name="context")
def transcription_orchestrator(context: df.DurableOrchestrationContext):
    source = context.get_input()
    validation = yield context.call_activity("validate_audio", source)
    if not validation["valid"]:
        rejection = {
            "subject": "Transcription rejected",
            "job": source["job_name"],
            "url": "N/A",
            "reason": validation["reason"],
        }
        yield context.call_activity("send_notification", rejection)
        return rejection
    yield context.call_activity("ensure_speech_webhook", None)
    job = yield context.call_activity("submit_transcription", source)
    completion = yield context.wait_for_external_event("speech_status")
    if isinstance(completion, str):
        completion = json.loads(completion)
    if completion["status"] == "Succeeded":
        yield context.call_activity("delete_upload", source)
        result = yield context.call_activity("finish_transcription", job)
        yield context.call_activity(
            "send_notification",
            {"subject": "Transcription job completed", **result},
        )
        return result
    failure = {
        "subject": "Transcription job failed",
        "job": job["displayName"],
        "url": "N/A",
        "reason": completion.get("error", {}).get("message", "Unknown Speech error"),
    }
    yield context.call_activity("send_notification", failure)
    return failure


@app.activity_trigger(input_name="source")
def validate_audio(source):
    return audio.validate(source["blob_url"])


@app.activity_trigger(input_name="source")
def submit_transcription(source):
    return speech.submit(
        source["blob_url"], source["job_name"], source["instance_id"]
    )


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


@app.activity_trigger(input_name="source")
def delete_upload(source):
    storage.delete_upload(source["blob_url"])


@app.activity_trigger(input_name="message")
def send_notification(message):
    notifications.send(message)


@app.function_name(name="speech_webhook")
@app.route(
    route="speech/webhook", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS
)
@app.durable_client_input(client_name="client")
async def speech_webhook(req: func.HttpRequest, client):
    validation_token = req.params.get("validationToken")
    if validation_token:
        return func.HttpResponse(validation_token, mimetype="text/plain")

    content = req.get_body()
    signature = req.headers.get("X-MicrosoftSpeechServices-Signature")
    if not webhooks.valid_signature(content, signature):
        return func.HttpResponse(status_code=401)

    payload = json.loads(content)
    transcription_id = payload["self"].split("?", 1)[0].rsplit("/", 1)[-1]
    job = speech.status({"id": transcription_id})
    instance_id = job.get("customProperties", {}).get("durableInstanceId")
    state = job.get("status")
    if instance_id and state in {"Succeeded", "Failed"}:
        await client.raise_event(
            instance_id,
            "speech_status",
            {"status": state, "error": job.get("error")},
        )
    return func.HttpResponse(status_code=202)


@app.activity_trigger(input_name="unused")
def ensure_speech_webhook(unused):
    speech.register_webhook(
        os.environ["SPEECH_WEBHOOK_URL"], webhooks.secret()
    )


@app.route(route="reports/export", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
def export_report(req: func.HttpRequest):
    return func.HttpResponse(
        json.dumps(storage.export_jobs()), mimetype="application/json"
    )
