import json
import os
from urllib.request import Request, urlopen

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient


def _secret(name):
    client = SecretClient(os.environ["KEY_VAULT_URL"], DefaultAzureCredential(managed_identity_client_id=os.environ.get("AZURE_CLIENT_ID")))
    return client.get_secret(name).value


def _post(url, payload):
    request = Request(url, json.dumps(payload).encode("utf-8"), {"Content-Type": "application/json"}, method="POST")
    with urlopen(request, timeout=15) as response:
        return response.status


def send(message):
    title = message["subject"]
    job = message["job"]
    url = message.get("url", "N/A")
    reason = message.get("reason")
    if os.environ.get("SLACK_NOTIFICATION", "false").lower() == "true":
        text = f"*{title}*\nJob: `{job}`\nTranscript: `{url}`"
        if reason:
            text += f"\nReason: {reason}"
        _post(_secret("slack-webhook"), {"text": text})
    if os.environ.get("TEAMS_NOTIFICATION", "false").lower() == "true":
        facts = [{"title": "Job", "value": job}, {"title": "Transcript", "value": url}]
        if reason:
            facts.append({"title": "Reason", "value": reason})
        _post(_secret("teams-webhook"), {
            "type": "message",
            "attachments": [{
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {"type": "AdaptiveCard", "version": "1.4", "body": [
                    {"type": "TextBlock", "weight": "Bolder", "text": title},
                    {"type": "FactSet", "facts": facts},
                ]},
            }],
        })
