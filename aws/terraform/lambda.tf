resource "aws_iam_role" "lambda_docx" {
  name = "${var.prefix}-${var.lambda_docx}-role"
  assume_role_policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        Action : "sts:AssumeRole",
        Effect : "Allow",
        Principal : {
          "Service" : "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_policy" "lambda_docx" {
  name = "${var.prefix}-${var.lambda_docx}-policy"
  policy = jsonencode(
    {
      "Version" : "2012-10-17",
      "Statement" : [
        {
          "Sid" : "VisualEditor0",
          "Effect" : "Allow",
          "Action" : [
            "s3:PutObject",
            "s3:DeleteObject",
            "s3:GetObject",
            "s3:ListBucket",
            "transcribe:GetTranscriptionJob",
            "logs:CreateLogStream",
            "logs:PutLogEvents",
          ],
          "Resource" : [
            "arn:aws:transcribe:*:${var.account}:transcription-job/*",
            "${aws_cloudwatch_log_group.docx.arn}:*",
            "${aws_s3_bucket.download.arn}/*",
            aws_s3_bucket.download.arn,
            "${aws_s3_bucket.upload.arn}/*",
            aws_s3_bucket.upload.arn
          ]
        },
        {
          "Sid" : "VisualEditor1",
          "Effect" : "Allow",
          "Action" : "logs:CreateLogGroup",
          "Resource" : "arn:aws:logs:${var.region}:${var.account}:*"
        },
        {
          "Sid" : "VisualEditor2",
          "Effect" : "Allow",
          "Action" : "transcribe:ListTranscriptionJobs",
          "Resource" : "*"
        }
      ]
    }
  )
}

resource "aws_cloudwatch_log_group" "docx" {
  name              = "/aws/lambda/${var.prefix}-${var.lambda_docx}"
  retention_in_days = 0
}

resource "aws_lambda_function" "docx" {
  depends_on = [
    aws_cloudwatch_log_group.docx
  ]
  function_name = "${var.prefix}-${var.lambda_docx}"
  memory_size   = 2048
  role          = aws_iam_role.lambda_docx.arn
  timeout       = 900
  image_uri     = "${var.account}.dkr.ecr.${var.region}.amazonaws.com/ats:latest"
  package_type  = "Image"
  #environment_variables = var.env_vars
  environment {
    variables = {
      MPLCONFIGDIR      = var.mpl
      WEBHOOK_URL       = var.webhook
      BUCKET            = aws_s3_bucket.download.id
      TIMEOUT           = var.docx_timeout
      CONFIDENCE        = var.confidence_score
      DOCX_MAX_DURATION = var.docx_max_duration
    }
  }
  image_config {
    command = [
      "transcribe_to_docx.lambda_handler",
    ]
    entry_point = []
  }
}

resource "aws_iam_role_policy_attachment" "docx" {
  role       = aws_iam_role.lambda_docx.id
  policy_arn = aws_iam_policy.lambda_docx.arn
}

resource "aws_lambda_event_source_mapping" "upload" {
  event_source_arn                   = aws_sqs_queue.audio_to_transcribe.arn
  function_name                      = module.transcribe.lambda_function_name
  batch_size                         = 10
  maximum_batching_window_in_seconds = 1
  function_response_types            = ["ReportBatchItemFailures"]
}

module "transcribe" {
  source  = "terraform-aws-modules/lambda/aws"
  version = ">= 7.14.0"

  function_name = "${var.prefix}-${var.lambda_ts}"
  handler       = "audio_to_transcribe.lambda_handler"
  runtime       = "python3.12"
  publish       = true
  source_path   = "../src/lambda/transcribe"
  environment_variables = {
    LOG_LEVEL   = "INFO"
    WEBHOOK_URL = var.webhook
    BUCKET      = aws_s3_bucket.download.id
  }

  attach_policy_json = true
  policy_json        = <<EOF
  {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor1",
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:ListBucket",
                "transcribe:GetTranscriptionJob",
                "sqs:ReceiveMessage",
                "sqs:DeleteMessage",
                "sqs:GetQueueAttributes"
            ],
            "Resource": [
                "${aws_sqs_queue.audio_to_transcribe.arn}",
                "${aws_s3_bucket.download.arn}/*",
                "${aws_s3_bucket.download.arn}",
                "${aws_s3_bucket.upload.arn}/*",
                "${aws_s3_bucket.upload.arn}"
            ]
        },
        {
            "Sid": "VisualEditor2",
            "Effect": "Allow",
            "Action": [
                "transcribe:StartTranscriptionJob"
            ],
            "Resource": "*"
        }
    ]
  }
  EOF

  tags = {
    Project = "ATS"
  }
}

module "teams-notification" {
  count   = var.teams_notification ? 1 : 0
  source  = "terraform-aws-modules/lambda/aws"
  version = ">= 7.14.0"

  function_name = "${var.prefix}-teams-notification"
  handler       = "sns_to_teams.lambda_handler"
  runtime       = "python3.12"
  publish       = true

  source_path = "../src/lambda/notifications"

  environment_variables = {
    LOG_LEVEL   = "INFO"
    WEBHOOK_URL = var.webhook
  }

  attach_policy_json = true
  policy_json        = <<EOF
  {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "logs:CreateLogGroup",
            "Resource": "arn:aws:logs:${var.region}:${var.account}:*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": [
                "arn:aws:logs:${var.region}:${var.account}:log-group:${var.prefix}-teams-notification:*"
            ]
        },
        {
            "Sid": "SNSReadOnlyAccess",
            "Effect": "Allow",
            "Action": [
                "sns:GetTopicAttributes",
                "sns:List*",
                "sns:CheckIfPhoneNumberIsOptedOut",
                "sns:GetEndpointAttributes",
                "sns:GetDataProtectionPolicy",
                "sns:GetPlatformApplicationAttributes",
                "sns:GetSMSAttributes",
                "sns:GetSMSSandboxAccountStatus",
                "sns:GetSubscriptionAttributes"
            ],
            "Resource": "${module.sns_topic.topic_arn}"
        }
    ]
  }
  EOF

  tags = {
    Project = "ATS"
  }
}

resource "aws_lambda_permission" "teams_notification_permission" {
  count         = var.teams_notification ? 1 : 0
  statement_id  = "AllowExecutionFromSNS"
  action        = "lambda:InvokeFunction"
  function_name = module.teams-notification[0].lambda_function_name
  principal     = "sns.amazonaws.com"
  source_arn    = module.sns_topic.topic_arn
}

resource "aws_sns_topic_subscription" "teams_notification_subscription" {
  count     = var.teams_notification ? 1 : 0
  topic_arn = module.sns_topic.topic_arn
  protocol  = "lambda"
  endpoint  = module.teams-notification[0].lambda_function_arn
}