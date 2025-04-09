import json
import os
from urllib.request import urlopen
from urllib.request import Request
 
def lambda_handler(event, context):
    webhook = os.environ['WEBHOOK_URL']
    title = event['Records'][0]['Sns']['Subject']
    content = event['Records'][0]['Sns']['Message']
 
    if not webhook or webhook == "DISABLED":
        print(f"notify_slack disabled, logging message instead: {title} {content}")

    if not title:
        title = "ATS notification"

    try:
        body = json.loads(content)
    except Exception as e:
        print(f"Failed to parse SNS message as JSON: {e}.")
        return

    job_name = body.get("job", "Unknown Job")
    s3uri = body.get("s3uri", "No S3 URI provided")
    slack_message = f"*Transcription job completed*\nJob Name:\n`{job_name}`\nTranscript available at:\n`{s3uri}`"
    message = {"blocks": [{"type": "section","text": {"type": "mrkdwn","text": slack_message}}]}
    request_data = json.dumps(message).encode("utf-8")
    req = Request(url=webhook, headers={"Content-Type": "application/json"}, data=request_data, method='POST')

    try:
        response = urlopen(req)
        if response.status != 200:
            print(f"Failed to notify Slack. Response: {response.status}")
        return response.status
    except Exception as e:
        print(e)

 