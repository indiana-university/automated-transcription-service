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
    ".mp4",
    ".ogg",
    ".opus",
    ".speex",
    ".spx",
    ".wav",
    ".wma",
}


def _name(blob_url):
    return PurePosixPath(unquote(urlparse(blob_url).path)).name


def _descriptor(data, offset):
    tag = data[offset]
    offset += 1
    length = 0
    for _ in range(4):
        value = data[offset]
        offset += 1
        length = (length << 7) | (value & 0x7F)
        if value & 0x80 == 0:
            end = offset + length
            if end > len(data):
                raise ValueError("MP4 descriptor extends beyond its box")
            return tag, data[offset:end]
    raise ValueError("Invalid MP4 descriptor length")


def _aac_channels(audio_config):
    bits = int.from_bytes(audio_config, "big")
    remaining = len(audio_config) * 8

    def read(count):
        nonlocal remaining
        remaining -= count
        if remaining < 0:
            raise ValueError("Incomplete AAC audio configuration")
        return (bits >> remaining) & ((1 << count) - 1)

    object_type = read(5)
    if object_type == 31:
        read(6)
    frequency_index = read(4)
    if frequency_index == 15:
        read(24)
    return read(4) or None


def _mp4_aac_channels(content):
    offset = 0
    while (atom := content.find(b"esds", offset)) != -1:
        offset = atom + 4
        try:
            tag, elementary_stream = _descriptor(content, atom + 8)
            if tag != 0x03 or len(elementary_stream) < 3:
                continue
            flags = elementary_stream[2]
            child = 3
            if flags & 0x80:
                child += 2
            if flags & 0x40:
                child += elementary_stream[child] + 1
            if flags & 0x20:
                child += 2
            tag, decoder = _descriptor(elementary_stream, child)
            if tag != 0x04 or len(decoder) < 13:
                continue
            tag, audio_config = _descriptor(decoder, 13)
            if tag != 0x05 or len(audio_config) < 2:
                continue

            return _aac_channels(audio_config)
        except (IndexError, ValueError):
            continue
    return None


def inspect_header(name, content, size):
    extension = PurePosixPath(name).suffix.lower()
    if extension not in PREFLIGHTABLE_EXTENSIONS:
        return {
            "valid": False,
            "reason": (
                f"Unsupported or unverifiable audio format '{extension or '(none)'}'. "
                "Use mono WAV, FLAC, MP3, MP4, OGG, Opus, WMA, AAC, or Speex audio."
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
    channels = metadata.channels
    if extension == ".mp4":
        channels = _mp4_aac_channels(content) or channels
    if channels is None:
        return {
            "valid": False,
            "reason": "The audio channel count could not be verified.",
        }
    if channels != 1:
        return {
            "valid": False,
            "reason": (
                f"Speaker diarization requires mono audio; this file has "
                f"{channels} channels."
            ),
        }
    return {
        "valid": True,
        "channels": channels,
        "format": extension.removeprefix("."),
        "sample_rate": metadata.samplerate,
    }


def validate(blob_url):
    client = BlobClient.from_blob_url(blob_url, credential=credential())
    size = client.get_blob_properties().size
    content = client.download_blob(offset=0, length=min(size, HEADER_BYTES)).readall()
    return inspect_header(_name(blob_url), content, size)
