data "aws_region" "current" {}

data "aws_caller_identity" "this" {}

data "aws_ecr_authorization_token" "token" {}

provider "docker" {
  registry_auth {
    address  = format("%v.dkr.ecr.%v.amazonaws.com", data.aws_caller_identity.this.account_id, data.aws_region.current.id)
    username = data.aws_ecr_authorization_token.token.user_name
    password = data.aws_ecr_authorization_token.token.password
  }
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
  runtime       = "python${var.python_version}"
  publish       = true
  source_path   = "../src/lambda/transcribe"
  environment_variables = {
    LOG_LEVEL = "INFO"
    BUCKET    = aws_s3_bucket.download.id
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
  runtime       = "python${var.python_version}"
  timeout       = 15 # Set a short timeout for notifications
  publish       = true

  source_path = "../src/lambda/notifications/teams"

  environment_variables = {
    LOG_LEVEL          = "INFO"
    WEBHOOK_SECRET_ARN = var.teams_notification ? aws_secretsmanager_secret.teams_webhook[0].arn : ""
  }

  attach_policy_json = true
  policy_json        = <<EOF
  {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "logs:CreateLogGroup",
            "Resource": "arn:aws:logs:${var.region}:${local.account}:*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": [
                "arn:aws:logs:${var.region}:${local.account}:log-group:${var.prefix}-teams-notification:*"
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
        },
        {
            "Sid": "SecretsManagerAccess",
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue"
            ],
            "Resource": "${var.teams_notification ? aws_secretsmanager_secret.teams_webhook[0].arn : "*"}"
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

module "export_jobs" {
  source  = "terraform-aws-modules/lambda/aws"
  version = ">= 7.14.0"

  function_name = "${var.prefix}-export-jobs"
  handler       = "export_jobs.lambda_handler"
  runtime       = "python${var.python_version}"
  timeout       = 300
  publish       = true
  source_path   = "../src/lambda/export"

  environment_variables = {
    DOWNLOAD_BUCKET = aws_s3_bucket.download.id
    DYNAMODB_TABLE  = module.dynamodb_table.dynamodb_table_id
  }

  attach_policy_json = true
  policy_json        = <<EOF
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Sid": "QueryDynamoDB",
        "Effect": "Allow",
        "Action": [
          "dynamodb:Query"
        ],
        "Resource": "${module.dynamodb_table.dynamodb_table_arn}"
      },
      {
        "Sid": "WriteToS3",
        "Effect": "Allow",
        "Action": [
          "s3:PutObject"
        ],
        "Resource": "${aws_s3_bucket.download.arn}/*"
      }
    ]
  }
  EOF

  tags = {
    Project = "ATS"
  }
}

module "docker_build" {
  source  = "terraform-aws-modules/lambda/aws//modules/docker-build"
  version = ">= 7.20.1"

  create_ecr_repo = true
  ecr_repo        = var.prefix
  ecr_repo_lifecycle_policy = jsonencode({
    "rules" : [
      {
        "rulePriority" : 1,
        "description" : "Keep only the last 2 images",
        "selection" : {
          "tagStatus" : "any",
          "countType" : "imageCountMoreThan",
          "countNumber" : 2
        },
        "action" : {
          "type" : "expire"
        }
      }
    ]
  })

  use_image_tag = false # If false, sha of the image will be used

  # use_image_tag = true
  # image_tag   = "2.0"

  source_path = "../src/lambda/docx"
  platform    = "linux/amd64"
  build_args = {
    PYTHON_VERSION = var.python_version # Specify the Python version to use in the Dockerfile
  }

}

module "docx" {
  source  = "terraform-aws-modules/lambda/aws"
  version = ">= 7.14.0"

  function_name  = "${var.prefix}-${var.lambda_docx}"
  description    = "Postprocessing for transcribe jobs"
  timeout        = 900
  memory_size    = 2048
  publish        = true
  create_package = false

  ##################
  # Container Image
  ##################
  package_type  = "Image"
  architectures = ["x86_64"] # ["arm64"]

  image_uri = module.docker_build.image_uri
  environment_variables = {
    MPLCONFIGDIR      = var.mpl
    BUCKET            = aws_s3_bucket.download.id
    TIMEOUT           = var.docx_timeout
    CONFIDENCE        = var.confidence_score
    DOCX_MAX_DURATION = var.docx_max_duration
    DOCUMENT_TITLE    = var.document_title
  }

  image_config_command = ["transcribe_to_docx.lambda_handler"]

  attach_policy_json = true
  policy_json        = <<EOF
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
          "transcribe:GetTranscriptionJob"
        ],
        "Resource" : [
          "arn:aws:transcribe:*:${local.account}:transcription-job/*",
          "${aws_s3_bucket.download.arn}/*",
          "${aws_s3_bucket.download.arn}",
          "${aws_s3_bucket.upload.arn}/*",
          "${aws_s3_bucket.upload.arn}"
        ]
      },
      {
        "Sid" : "VisualEditor2",
        "Effect" : "Allow",
        "Action" : "transcribe:ListTranscriptionJobs",
        "Resource" : "*"
      }
    ]
  }
  EOF

  tags = {
    Project = "ATS"
  }

}

module "slack-notification" {
  count   = var.slack_notification ? 1 : 0
  source  = "terraform-aws-modules/lambda/aws"
  version = ">= 7.14.0"

  function_name = "${var.prefix}-slack-notification"
  handler       = "sns_to_slack.lambda_handler"
  runtime       = "python${var.python_version}"
  timeout       = 15 # Set a short timeout for notifications
  publish       = true

  source_path = "../src/lambda/notifications/slack"

  environment_variables = {
    LOG_LEVEL          = "INFO"
    WEBHOOK_SECRET_ARN = var.slack_notification ? aws_secretsmanager_secret.slack_webhook[0].arn : ""
  }

  attach_policy_json = true
  policy_json        = <<EOF
  {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "logs:CreateLogGroup",
            "Resource": "arn:aws:logs:${var.region}:${local.account}:*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": [
                "arn:aws:logs:${var.region}:${local.account}:log-group:${var.prefix}-slack-notification:*"
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
        },
        {
            "Sid": "SecretsManagerAccess",
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue"
            ],
            "Resource": "${var.slack_notification ? aws_secretsmanager_secret.slack_webhook[0].arn : "*"}"
        }
    ]
  }
  EOF

  tags = {
    Project = "ATS"
  }
}

resource "aws_lambda_permission" "slack_notification_permission" {
  count         = var.slack_notification ? 1 : 0
  statement_id  = "AllowExecutionFromSNS"
  action        = "lambda:InvokeFunction"
  function_name = module.slack-notification[0].lambda_function_name
  principal     = "sns.amazonaws.com"
  source_arn    = module.sns_topic.topic_arn
}

resource "aws_sns_topic_subscription" "slack_notification_subscription" {
  count     = var.slack_notification ? 1 : 0
  topic_arn = module.sns_topic.topic_arn
  protocol  = "lambda"
  endpoint  = module.slack-notification[0].lambda_function_arn
}