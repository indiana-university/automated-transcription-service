# Generating Reports

Job details are saved to DynamoDB and there is a lambda that can be run to generate a CSV export in the downloads bucket. The lambda function is called `ats-export-jobs`. Create an EventBridge rule to run this on a schedule.

Reports can also be generated from the CloudWatch logs. Begin by opening the CloudWatch console at https://console.aws.amazon.com/cloudwatch/.

Next, click on Logs Insights and select the /aws/lambda/transcribe-to-docx log group from the drop-down list.

Edit the query as follows:
```
fields @timestamp as Timestamp
| parse @message "'TranscriptionJobName': '*'" as TranscriptionJobName
| parse @message "'LanguageCodes': [*]" as LC1
| fields replace(LC1,"'",'"') as LC2
| fields concat("[",LC2,"]") as LanguageCodes
| sort @timestamp desc
| filter @message like /\QJob info: {'TranscriptionJobName': \E.*\Q, 'TranscriptionJobStatus': 'COMPLETED'\E.*\Q, 'DurationInSeconds'/
| display Timestamp, TranscriptionJobName, LanguageCodes
```

Click on the date range and select custom. Enter a start and end date.

Click on Run query.

Click on Export results and choose `Download table (JSON)`.

The report will be downloaded as a JSON file. 

Optional: Use the reports.py script to convert the JSON to a CSV file. Note that this script assumes job names start with a username, e.g. jsmith_full_job_name_123.
