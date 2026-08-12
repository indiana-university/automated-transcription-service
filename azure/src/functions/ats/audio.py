from io import BytesIO
from pathlib import PurePosixPath
from urllib.parse import unquote, urlparse

from azure.storage.blob import BlobClient
from tinytag import TinyTag, TinyTagException

from ats.storage import credential


HEADER_BYTES = 1024 * 1024
PREFLIGHTABLE_EXTENSIONS = {
    ".aac",
    ".flac",
    ".mp3",
    ".ogg",
    ".opus",
    ".speex",
    ".spx",
    ".wav",
    ".wma",
}


def _name(blob_url):
    return PurePosixPath(unquote(urlparse(blob_url).path)).name


def inspect_header(name, content, size):
    extension = PurePosixPath(name).suffix.lower()
    if extension not in PREFLIGHTABLE_EXTENSIONS:
        return {
            "valid": False,
            "reason": (
                f"Unsupported or unverifiable audio format '{extension or '(none)'}'. "
                "Use mono WAV, FLAC, MP3, OGG, Opus, WMA, AAC, or Speex audio."
            ),
        }
    if size == 0:
        return {"valid": False, "reason": "The uploaded audio file is empty."}
    try:
        metadata = TinyTag.get(
            filename=name,
            file_obj=BytesIO(content),
            tags=False,
            duration=True,
        )
    except (TinyTagException, ValueError, OSError) as error:
        return {
            "valid": False,
            "reason": f"Audio metadata could not be read: {error}",
        }
    if metadata.channels is None:
        return {
            "valid": False,
            "reason": "The audio channel count could not be verified.",
        }
    if metadata.channels != 1:
        return {
            "valid": False,
            "reason": (
                f"Speaker diarization requires mono audio; this file has "
                f"{metadata.channels} channels."
            ),
        }
    return {
        "valid": True,
        "channels": metadata.channels,
        "format": extension.removeprefix("."),
        "sample_rate": metadata.samplerate,
    }


def validate(blob_url):
    client = BlobClient.from_blob_url(blob_url, credential=credential())
    size = client.get_blob_properties().size
    content = client.download_blob(offset=0, length=min(size, HEADER_BYTES)).readall()
    return inspect_header(_name(blob_url), content, size)
