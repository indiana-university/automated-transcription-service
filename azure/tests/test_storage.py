import sys
from pathlib import Path
from unittest.mock import Mock, patch

from azure.core.exceptions import ResourceNotFoundError

FUNCTIONS_ROOT = Path(__file__).parents[1] / "src" / "functions"
sys.path.insert(0, str(FUNCTIONS_ROOT))

from ats import storage  # noqa: E402


def test_delete_upload_uses_blob_url_and_managed_identity():
    client = Mock()
    identity = object()

    with (
        patch.object(storage, "credential", return_value=identity),
        patch.object(storage.BlobClient, "from_blob_url", return_value=client) as from_blob_url,
    ):
        storage.delete_upload("https://example.test/upload/sample.ogg")

    from_blob_url.assert_called_once_with(
        "https://example.test/upload/sample.ogg", credential=identity
    )
    client.delete_blob.assert_called_once_with()


def test_delete_upload_is_idempotent_when_blob_is_already_gone():
    client = Mock()
    client.delete_blob.side_effect = ResourceNotFoundError("missing")

    with patch.object(storage.BlobClient, "from_blob_url", return_value=client):
        storage.delete_upload("https://example.test/upload/sample.ogg")
