import json
import os
import boto3
from urllib.request import urlopen
from urllib.request import Request

def get_webhook_url():
    """Get webhook URL from AWS Secrets Manager using WEBHOOK_SECRET_ARN.
    
    Returns:
        str: The webhook URL from the secret, or 'DISABLED' if WEBHOOK_SECRET_ARN 
             is not set/empty or if an exception occurs during secret retrieval.
    """
    webhook_secret_arn = os.environ.get('WEBHOOK_SECRET_ARN')
    
    if not webhook_secret_arn:
        return 'DISABLED'
    
    try:
        secrets_client = boto3.client('secretsmanager')
        response = secrets_client.get_secret_value(SecretId=webhook_secret_arn)
        secret_data = json.loads(response['SecretString'])
        return secret_data.get('webhook_url', 'DISABLED')
    except Exception:
        return 'DISABLED'
 
def lambda_handler(event, context):
    webhook = get_webhook_url()
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

 