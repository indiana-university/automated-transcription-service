import base64
import hashlib
import hmac
import sys
from pathlib import Path
from unittest.mock import patch


FUNCTIONS_ROOT = Path(__file__).parents[1] / "src" / "functions"
sys.path.insert(0, str(FUNCTIONS_ROOT))

from ats import webhooks  # noqa: E402


def test_valid_signature_uses_base64_encoded_hmac_sha256():
    content = b'{"self":"transcription"}'
    signature = base64.b64encode(
        hmac.new(b"secret", content, hashlib.sha256).digest()
    ).decode()

    with patch.object(webhooks, "secret", return_value="secret"):
        assert webhooks.valid_signature(content, signature)
        assert not webhooks.valid_signature(content + b"changed", signature)


def test_missing_signature_is_rejected_without_loading_secret():
    with patch.object(webhooks, "secret") as secret:
        assert not webhooks.valid_signature(b"content", None)

    secret.assert_not_called()
