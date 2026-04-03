import json
import os
import boto3
from urllib.request import urlopen
from urllib.request import Request

def get_webhook_url():
    """Retrieve webhook URL from AWS Secrets Manager"""
    secret_arn = os.environ.get('WEBHOOK_SECRET_ARN')
    
    if not secret_arn or secret_arn == "":
        return 'DISABLED'
    
    try:
        secrets_client = boto3.client('secretsmanager')
        response = secrets_client.get_secret_value(SecretId=secret_arn)
        return response['SecretString']
    except Exception as e:
        print(f"Failed to retrieve webhook URL from Secrets Manager: {e}")
        return 'DISABLED'

def lambda_handler(event, context):
    webhook = get_webhook_url()
    title = event['Records'][0]['Sns']['Subject']
    content = event['Records'][0]['Sns']['Message']

    if not webhook or webhook == "DISABLED":
        print(f"notify_teams disabled, logging message instead: {title} {content}")
        return

    if not title:
        title = "ATS notification"

    try:
        body = json.loads(content)
    except Exception as e:
        print(f"Failed to parse SNS message as JSON: {e}.")
        return

    job_name = body.get("job", "Unknown Job")
    s3uri = body.get("s3uri", "No S3 URI provided")
    message = {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "contentUrl": None,
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": [
                        {
                            "type": "TextBlock",
                            "size": "Medium",
                            "weight": "Bolder",
                            "text": title,
                        },
                        {
                            "type": "FactSet",
                            "facts": [
                                {"title": "Job Name", "value": job_name},
                                {"title": "Transcript S3 URI", "value": s3uri},
                            ],
                        },
                    ],
                },
            }
        ],
    }
    request_data = json.dumps(message).encode("utf-8")
    req = Request(url=webhook, headers={"Content-Type": "application/json"}, data=request_data, method='POST')

    try:
        response = urlopen(req)
        if response.status != 200:
            print(f"Failed to notify Teams. Response: {response.status}")
        return response.status
    except Exception as e:
        print(e)

 