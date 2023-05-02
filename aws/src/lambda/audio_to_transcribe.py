import boto3
from urllib.parse import unquote_plus
import json
from datetime import datetime as dt
import os
import uuid
import re

import ats_utilities

# Get current date for S3 folder name:
today = dt.now().strftime("%Y%m%d")

# S3 client to read/write files
s3 = boto3.client('s3')

# Transcribe client to read job results
ts_client = boto3.client('transcribe')

#Color coding for Teams messages
RED = "FF0000"

def lambda_handler(event, context):
    """
    Entrypoint for the transcribe Lambda function. Pulls batch of messages from SQS standard queue.
    """
    print(f"audio_to_transcribe.lambda_handler started")

    s3bucketOutput = os.environ["BUCKET"]
    WEBHOOK = os.environ['WEBHOOK_URL']
    batch_failures = []
    for record in event["Records"]:
        event_message = json.loads(record["body"])
        print(f"Event message: {event_message}")

        recordZero = event_message['Records'][0]
        # unquote_plus to handle spaces
        s3object = unquote_plus(recordZero['s3']['object']['key'])
        s3bucketInput = recordZero['s3']['bucket']['name']

        s3Path = "s3://" + s3bucketInput + "/" + s3object
        jobName = re.sub('[^a-zA-Z0-9_\-.]+','_', s3object) + '-' + str(uuid.uuid4())

        try:
            response = ts_client.start_transcription_job(
                TranscriptionJobName=jobName,
                Settings={
                    'ShowSpeakerLabels': True,
                    'MaxSpeakerLabels': 10,
                },
                IdentifyMultipleLanguages=True,
                Media={
                    'MediaFileUri': s3Path
                },
                OutputBucketName = s3bucketOutput,
                OutputKey = today + "/"
            )
        except Exception as e:
            print(e)
            title = "Could not start transcription job"
            message = f"File name:<br><pre>{s3Path}</pre><br>Please review CloudWatch logs for more details."
            color = RED
            ats_utilities.notify_teams(WEBHOOK, title, message, color)
            batch_failures.append({"itemIdentifier": record["messageId"]})
            continue

    # Send failed messages back to queue for retry
    sqs_response = {}
    if len(batch_failures) > 0:
        sqs_response["batchItemFailures"] = batch_failures

    print(f"Function ending. Response={sqs_response}")
    return sqs_response
