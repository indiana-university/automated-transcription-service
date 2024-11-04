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
          "Next": "Yes"
        }
      ],
      "Default": "No"
    },
    "No": {
      "Type": "Fail",
      "ErrorPath": "$.detail.TranscriptionJobStatus"
    },
    "Yes": {
      "Type": "Pass",
      "End": true
    }
  }
}
EOF

  #role_arn = aws_iam_role.step_function_role.arn

  tags = {
    Project = "ATS"
  }
}