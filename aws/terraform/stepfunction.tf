module "step_function" {
  source  = "terraform-aws-modules/step-functions/aws"
  version = ">= 4.2.0"

  name = "${var.prefix}-postprocessing"

  definition = <<EOF
  {
    "Comment": "Step function to perform post-processing on Transcriptions.",
    "StartAt": "Transcribed?",
    "States": {
      "Transcribed?": {
        "Comment": "Check to see if Transcribe job completed.",
        "Type": "Choice",
        "Choices": [
          {
            "Variable": "$.detail.TranscriptionJobStatus",
            "StringEquals": "COMPLETED",
            "Next": "Create DOCX"
          }
        ],
        "Default": "Transcribe failed notification"
      },
      "Transcribe failed notification": {
        "Type": "Task",
        "Resource": "arn:aws:states:::sns:publish",
        "Parameters": {
          "Message": "Transcribe job failed. See CloudWatch logs for details.",
          "TopicArn": "${module.sns_topic.topic_arn}"
        },
        "Next": "ERROR"
      },
      "Create DOCX": {
        "Type": "Task",
        "Resource": "arn:aws:states:::lambda:invoke",
        "Parameters": {
          "Payload.$": "$",
          "FunctionName": "${aws_lambda_function.docx.arn}"
        },
        "Retry": [
          {
            "ErrorEquals": [
              "Lambda.ServiceException",
              "Lambda.AWSLambdaException",
              "Lambda.SdkClientException",
              "Lambda.TooManyRequestsException"
            ],
            "IntervalSeconds": 1,
            "MaxAttempts": 3,
            "BackoffRate": 2
          }
        ],
        "Next": "ATS Notification"
      },
      "ATS Notification": {
        "Type": "Task",
        "Resource": "arn:aws:states:::aws-sdk:sns:publish",
        "Parameters": {
          "TopicArn": "${module.sns_topic.topic_arn}",
          "Subject.$": "$.body.subject",
          "MessageStructure": "json",
          "Message": {
            "default.$": "$.body.default",
            "lambda.$": "$.body.lambda"
          }
        },
        "Next": "Choice",
        "InputPath": "$.Payload",
        "ResultPath": null
      },
      "Choice": {
        "Type": "Choice",
        "Choices": [
          {
            "Variable": "$.Payload.statusCode",
            "NumericEquals": 200,
            "Next": "DynamoDB PutItem"
          }
        ],
        "Default": "ERROR"
      },
      "DynamoDB PutItem": {
        "Type": "Task",
        "Resource": "arn:aws:states:::dynamodb:putItem",
        "Parameters": {
          "TableName": "${module.dynamodb_table.dynamodb_table_id}",
          "Item": {
            "PK": {
              "S": "jobs"
            },
            "SK": {
              "S.$": "$.body.job"
            },
            "Languages": {
              "S.$": "$.body.languages"
            },
            "TotalDuration": {
              "N.$": "States.Format('{}',$.body.duration)"
            },
            "Confidence": {
              "N.$": "$.body.confidence"
            },
            "Created": {
              "S.$": "$.body.created"
            }
          }
        },
        "Next": "COMPLETED",
        "InputPath": "$.Payload"
      },
      "ERROR": {
        "Type": "Fail"
      },
      "COMPLETED": {
        "Type": "Succeed"
      }
    }
  }
  EOF

  service_integrations = {
    lambda = {
      lambda = [
        aws_lambda_function.docx.arn
      ]
    },
    sns = {
      sns = [
        module.sns_topic.topic_arn
      ]
    },
    dynamodb = {
      dynamodb = [
        module.dynamodb_table.dynamodb_table_arn
      ]
    }
  }

  tags = {
    Project = "ATS"
  }
}