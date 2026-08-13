import json
import os
import re
import secrets
from pathlib import PurePosixPath
from urllib.error import HTTPError
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobClient


def _credential():
    return DefaultAzureCredential(managed_identity_client_id=os.environ.get("AZURE_CLIENT_ID"))


def _request(method, url, body=None):
    token = _credential().get_token("https://cognitiveservices.azure.com/.default").token
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = Request(url, data=data, method=method)
    request.add_header("Authorization", f"Bearer {token}")
    request.add_header("Content-Type", "application/json")
    try:
        with urlopen(request, timeout=60) as response:
            return json.load(response)
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Speech API returned {error.code}: {detail}") from error


def _api_url(path):
    endpoint = os.environ["SPEECH_ENDPOINT"].rstrip("/")
    version = os.environ.get("SPEECH_API_VERSION", "2025-10-15")
    separator = "&" if "?" in path else "?"
    return f"{endpoint}{path}{separator}api-version={version}"


def job_name(blob_url):
    filename = PurePosixPath(unquote(urlparse(blob_url).path)).name
    safe_filename = re.sub(r"[^a-zA-Z0-9_.-]+", "_", filename)
    suffix = f"{secrets.randbelow(100_000_000):08d}"
    return f"{safe_filename}-{suffix}"


def submit(blob_url, display_name):
    locales = [item.strip() for item in os.environ.get("SPEECH_LOCALES", "en-US").split(",")]
    properties = {
        "diarization": {"enabled": True, "maxSpeakers": int(os.environ.get("MAX_SPEAKERS", "10"))},
        "timeToLiveHours": 48,
        "wordLevelTimestampsEnabled": True,
        "displayFormWordLevelTimestampsEnabled": True,
    }
    if len(locales) > 1:
        properties["languageIdentification"] = {"candidateLocales": locales, "mode": "Single"}
    payload = {
        "contentUrls": [blob_url],
        "displayName": display_name,
        "locale": locales[0],
        "properties": properties,
    }
    job = _request("POST", _api_url("/speechtotext/transcriptions:submit"), payload)
    job["displayName"] = display_name
    if "id" not in job:
        job["id"] = job["self"].split("?", 1)[0].rsplit("/", 1)[-1]
    return job


def status(job):
    return _request("GET", _api_url(f"/speechtotext/transcriptions/{job['id']}"))


def result(job):
    files = _request(
        "GET",
        _api_url(f"/speechtotext/transcriptions/{job['id']}/files?sasValidityInSeconds=0"),
    )
    transcript = next(item for item in files["values"] if item["kind"] == "Transcription")
    client = BlobClient.from_blob_url(transcript["links"]["contentUrl"], credential=_credential())
    return json.loads(client.download_blob().readall())
