# Notifications

The postprocessing workflow generates notifications that are sent to an SNS topic. You can simply subscribe an email to this topic and receive notifications when a transcriptions is generated. If you use Teams or Slack, there are also Lambda functions that can be created and will automatically be subscribed to the SNS topic.

Each notification is controlled by a variable in Terraform that determines whether or not the Lambda is created and subscribed to the SNS topic. The following variables are available:
```
teams_notification
slack_notification
```

Both variables default to false, but if you set either (or both) to true, then the Lambda function will be created and subscribed to the SNS topic. The Lambda function will send a message to the SNS topic when a transcription is generated.

The provided Lambdas assume that you have created a webhook in Teams or Slack. There are two additional Terraform variables that you can use to specify the webhook URL for each service:
```
teams_webhook
slack_webhook
```

See the Teams and Slack documentation for details about creating a webhook.