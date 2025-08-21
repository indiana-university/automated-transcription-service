import boto3
import json
import os
import uuid
import re
from urllib.parse import unquote_plus
from datetime import datetime as dt

# Get current date for S3 folder name
today = dt.now().strftime("%Y%m%d")

def lambda_handler(event, context):
    """
    Entrypoint for the step trigger Lambda function. 
    Transforms S3 event into step function input and starts the workflow.
    """
    print("audio_to_transcribe.lambda_handler started - now triggering step function")
    
    step_functions = boto3.client('stepfunctions')
    state_machine_arn = os.environ['STATE_MACHINE_ARN']
    
    batch_failures = []
    
    for record in event["Records"]:
        try:
            # Parse S3 event from SQS message
            event_message = json.loads(record["body"])
            s3_record = event_message['Records'][0]
            
            # Extract S3 details
            s3_object = unquote_plus(s3_record['s3']['object']['key'])
            s3_bucket = s3_record['s3']['bucket']['name']
            
            # Generate job name similar to original audio_to_transcribe
            job_name = re.sub(r'[^a-zA-Z0-9_\-.]+', '_', s3_object) + '-' + str(uuid.uuid4())
            
            # Construct S3 URI
            media_uri = f"s3://{s3_bucket}/{s3_object}"
            
            # Create step function input
            step_input = {
                "job_name": job_name,
                "media_uri": media_uri,
                "output_prefix": f"{today}/",
                "elapsed_time": 0,
                "original_s3_key": s3_object,
                "original_s3_bucket": s3_bucket
            }
            
            print(f"Starting step function with input: {step_input}")
            
            # Start step function execution
            response = step_functions.start_execution(
                stateMachineArn=state_machine_arn,
                name=f"ats-{job_name}",
                input=json.dumps(step_input)
            )
            
            print(f"Step function execution started: {response['executionArn']}")
            
        except Exception as e:
            print(f"Error processing record: {e}")
            batch_failures.append({"itemIdentifier": record["messageId"]})
            continue
    
    # Return batch failures for SQS retry
    sqs_response = {}
    if len(batch_failures) > 0:
        sqs_response["batchItemFailures"] = batch_failures
    
    print(f"Function ending. Response={sqs_response}")
    return sqs_response