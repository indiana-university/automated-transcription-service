import base64
import hashlib
import hmac
import os

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient


def secret():
    credential = DefaultAzureCredential(
        managed_identity_client_id=os.environ.get("AZURE_CLIENT_ID")
    )
    client = SecretClient(os.environ["KEY_VAULT_URL"], credential)
    return client.get_secret("speech-webhook-secret").value


def valid_signature(content, signature):
    if not signature:
        return False
    digest = hmac.new(secret().encode(), content, hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode()
    return hmac.compare_digest(expected, signature)
