module "step_function" {
  source  = "terraform-aws-modules/step-functions/aws"
  version = ">= 4.2.0"

  name = "${var.prefix}-ats-workflow"

  definition = <<EOF
  {
    "Comment": "Step function to handle entire ATS workflow from file upload to completion.",
    "StartAt": "Start Transcribe Job",
    "States": {
      "Start Transcribe Job": {
        "Comment": "Start transcription job for uploaded file.",
        "Type": "Task",
        "Resource": "arn:aws:states:::aws-sdk:transcribe:startTranscriptionJob",
        "Parameters": {
          "TranscriptionJobName.$": "$.job_name",
          "LanguageCode": "en-US",
          "Media": {
            "MediaFileUri.$": "$.media_uri"
          },
          "OutputBucketName": "${aws_s3_bucket.download.id}",
          "OutputKey.$": "$.output_prefix",
          "Settings": {
            "ShowSpeakerLabels": true,
            "MaxSpeakerLabels": 10
          },
          "IdentifyMultipleLanguages": true,
          "Tags": [
            {
              "Key": "Source",
              "Value": "ATS"
            },
            {
              "Key": "Project", 
              "Value": "ATS"
            }
          ]
        },
        "Next": "Wait for Transcribe Job",
        "Retry": [
          {
            "ErrorEquals": [
              "States.TaskFailed"
            ],
            "IntervalSeconds": 2,
            "MaxAttempts": 3,
            "BackoffRate": 2.0
          }
        ],
        "Catch": [
          {
            "ErrorEquals": ["States.ALL"],
            "Next": "Transcribe failed notification",
            "ResultPath": "$.error"
          }
        ]
      },
      "Wait for Transcribe Job": {
        "Comment": "Poll transcribe job status until completion.",
        "Type": "Wait",
        "Seconds": 30,
        "Next": "Get Transcribe Job Status"
      },
      "Get Transcribe Job Status": {
        "Comment": "Get the current status of the transcribe job.",
        "Type": "Task",
        "Resource": "arn:aws:states:::aws-sdk:transcribe:getTranscriptionJob",
        "Parameters": {
          "TranscriptionJobName.$": "$.job_name"
        },
        "Next": "Check Transcription Status",
        "ResultPath": "$.TranscriptionJobResult",
        "Retry": [
          {
            "ErrorEquals": [
              "States.TaskFailed"
            ],
            "IntervalSeconds": 2,
            "MaxAttempts": 3,
            "BackoffRate": 2.0
          }
        ]
      },
      "Check Transcription Status": {
        "Comment": "Check if transcription completed successfully.",
        "Type": "Choice",
        "Choices": [
          {
            "Variable": "$.TranscriptionJobResult.TranscriptionJob.TranscriptionJobStatus",
            "StringEquals": "COMPLETED",
            "Next": "Transform for DOCX"
          },
          {
            "Variable": "$.TranscriptionJobResult.TranscriptionJob.TranscriptionJobStatus", 
            "StringEquals": "IN_PROGRESS",
            "Next": "Check Timeout"
          }
        ],
        "Default": "Transcribe failed notification"
      },
      "Transform for DOCX": {
        "Comment": "Transform data for DOCX lambda input format.",
        "Type": "Pass",
        "Parameters": {
          "TranscriptionJob.$": "$.TranscriptionJobResult.TranscriptionJob"
        },
        "Next": "Create DOCX"
      },
      "Check Timeout": {
        "Comment": "Check if we have exceeded the timeout.",
        "Type": "Choice",
        "Choices": [
          {
            "Variable": "$.elapsed_time",
            "NumericGreaterThanEquals": ${var.transcribe_job_timeout_seconds},
            "Next": "Transcribe timeout notification"
          }
        ],
        "Default": "Update Elapsed Time"
      },
      "Update Elapsed Time": {
        "Comment": "Update elapsed time counter and preserve state for next iteration.",
        "Type": "Pass",
        "Parameters": {
          "elapsed_time.$": "States.MathAdd($.elapsed_time, 30)",
          "job_name.$": "$.job_name",
          "media_uri.$": "$.media_uri", 
          "output_prefix.$": "$.output_prefix",
          "original_s3_key.$": "$.original_s3_key",
          "original_s3_bucket.$": "$.original_s3_bucket"
        },
        "Next": "Wait for Transcribe Job"
      },
      "Transcribe timeout notification": {
        "Type": "Task",
        "Resource": "arn:aws:states:::sns:publish",
        "Parameters": {
          "Message": "Transcribe job timed out after ${var.transcribe_job_timeout_seconds} seconds. See CloudWatch logs for details.",
          "TopicArn": "${module.sns_topic.topic_arn}"
        },
        "Next": "ERROR"
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
          "Payload": {
            "detail": {
              "TranscriptionJobName.$": "$.TranscriptionJob.TranscriptionJobName",
              "TranscriptionJobStatus.$": "$.TranscriptionJob.TranscriptionJobStatus"
            }
          },
          "FunctionName": "${module.docx.lambda_function_arn}"
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
            "default": "States.Format('Transcription job {} completed. Transcript available at {}', $.body.job_name, $.body.s3uri)",
            "lambda.$": "States.JsonToString($.body)"
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
        module.docx.lambda_function_arn
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

  attach_policy_statements = true
  policy_statements = {
    transcribe = {
      effect = "Allow"
      actions = [
        "transcribe:StartTranscriptionJob",
        "transcribe:GetTranscriptionJob",
        "transcribe:TagResource"
      ]
      resources = ["*"]
    }
    s3_read = {
      effect = "Allow"
      actions = [
        "s3:GetObject"
      ]
      resources = [
        "${aws_s3_bucket.upload.arn}/*"
      ]
    }
    s3_write = {
      effect = "Allow"
      actions = [
        "s3:PutObject"
      ]
      resources = [
        "${aws_s3_bucket.download.arn}/*"
      ]
    }
  }

  tags = {
    Project = "ATS"
  }
}