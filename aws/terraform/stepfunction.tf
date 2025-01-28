resource "aws_iam_role" "step_function_role" {
  name = "${var.prefix}-step-function-role"
  assume_role_policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Principal" : {
          "Service" : "states.amazonaws.com"
        },
        "Action" : "sts:AssumeRole"
      }
    ]
  })
}

# resource "aws_iam_policy" "step_function_policy" {
#   name = "${var.prefix}-step-function-policy"
#   policy = jsonencode({
#     "Version" : "2012-10-17",
#     "Statement" : [
#       {
#         "Effect" : "Allow",
#         "Action" : [
#           "logs:CreateLogGroup",
#           "logs:CreateLogStream",
#           "logs:PutLogEvents"
#         ],
#         "Resource" : "*"
#       }
#     ]
#   })
# }

# resource "aws_iam_role_policy_attachment" "step_function_policy_attachment" {
#   role       = aws_iam_role.step_function_role.name
#   policy_arn = aws_iam_policy.step_function_policy.arn
# }

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
      "Default": "ERROR"
    },
    "Create DOCX": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke",
      "Parameters": {
        "Payload.$": "$",
        "FunctionName": "${aws_lambda_function.docx.arn}:$LATEST"
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
      "Next": "DynamoDB PutItem",
      "ResultPath": null
    },
    "DynamoDB PutItem": {
      "Type": "Task",
      "Resource": "arn:aws:states:::dynamodb:putItem",
      "Parameters": {
        "TableName": "ats-jobs-table",
        "Item": {
          "PK": {
            "S": "jobs"
          },
          "SK": {
            "S.$": "$.detail.TranscriptionJobName"
          }
        }
      },
      "Next": "COMPLETED"
    },
    "ERROR": {
      "Type": "Fail",
      "ErrorPath": "$.detail.TranscriptionJobStatus"
    },
    "COMPLETED": {
      "Type": "Succeed"
    }
  }
}
EOF

  #role_arn = aws_iam_role.step_function_role.arn

  tags = {
    Project = "ATS"
  }
}