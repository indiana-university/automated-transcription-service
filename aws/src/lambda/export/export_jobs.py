import os
import csv
import io
import boto3
from boto3.dynamodb.conditions import Key

def lambda_handler(event, context):
    # Initialize DynamoDB and S3 clients
    dynamodb = boto3.resource('dynamodb')
    table_name = os.environ['DYNAMODB_TABLE']
    table = dynamodb.Table(table_name)
    s3 = boto3.client('s3')
    download_bucket = os.environ['DOWNLOAD_BUCKET']

    # Query the DynamoDB table for records where PK equals "jobs"
    response = table.query(
        KeyConditionExpression=Key('PK').eq("jobs")
    )
    records = response.get('Items', [])

    # Create CSV file in memory
    output = io.StringIO()
    writer = csv.writer(output)
    if records:
        orig_keys = list(records[0].keys())
        header = []
        use_keys = []
        for k in orig_keys:
            if k == "PK":
                continue
            elif k == "SK":
                header.append("Job")
                use_keys.append(k)
            else:
                header.append(k)
                use_keys.append(k)
        writer.writerow(header)
        for item in records:
            writer.writerow([item.get(k, "") for k in use_keys])
    else:
        writer.writerow(["No records found"])

    csv_content = output.getvalue()
    output.close()

    # Save CSV file to the download S3 bucket
    filename = "transcribe_jobs.csv"
    key = f"export/{filename}"
    s3.put_object(Bucket=download_bucket, Key=key, Body=csv_content)

    return {
        'statusCode': 200,
        'body': f"CSV file '{filename}' created with {len(records)} records."
    }