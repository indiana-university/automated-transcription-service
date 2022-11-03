import boto3
import sys
import urllib.parse

s3 = boto3.client('s3')

#TODO: create handler for Transcribe job(s), e.g.,:
# def transcribe_handler():

#TODO: Add functions for ATS, e.g., creating docx from JSON. Ideally usable from both Lambda and CLI.

def docx_handler(event, context):
    #print("Received event: " + json.dumps(event, indent=2))

    # Get the object from the event and show its content type
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        print("CONTENT TYPE: " + response['ContentType'])
        return response['ContentType']
    except Exception as e:
        print(e)
        print('Error getting object {} from bucket {}. Make sure they exist and your bucket is in the same region as this function.'.format(key, bucket))
        raise e

#TODO: Add back in a "main" function for CLI.