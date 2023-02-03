
data "aws_caller_identity" "current" {}

locals {
  prefix              = "ats"
  account_id          = data.aws_caller_identity.current.account_id
  ecr_repository_name = "${local.prefix}-lambda-container"
  ecr_image_tag       = "latest"
}

resource "aws_iam_role" "lambda_docx" {
  name = "${local.prefix}-lambda-docx-role"
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
  name = "${local.prefix}-lambda-docx-policy"
  policy = jsonencode(
    {
      "Version" : "2012-10-17",
      "Statement" : [
        {
          "Sid" : "VisualEditor0",
          "Effect" : "Allow",
          "Action" : [
            "sqs:DeleteMessage",
            "s3:PutObject",
            "s3:GetObject",
            "transcribe:GetTranscriptionJob",
            "logs:CreateLogStream",
            "sqs:ReceiveMessage",
            "sqs:GetQueueAttributes",
            "s3:ListBucket",
            "logs:PutLogEvents"
          ],
          "Resource" : [
            "arn:aws:transcribe:*:${var.account}:transcription-job/*",
            "${aws_cloudwatch_log_group.transcribe_to_docx.arn}:*",
            aws_sqs_queue.transcribe_to_docx.arn,
            "${aws_s3_bucket.download.arn}/*",
            aws_s3_bucket.download.arn
          ]
        },
        {
          "Sid" : "VisualEditor1",
          "Effect" : "Allow",
          "Action" : "logs:CreateLogGroup",
          "Resource" : "arn:aws:logs:us-east-1:${var.account}:*"
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

resource "aws_cloudwatch_log_group" "transcribe_to_docx" {
  name              = var.lambda_docx
  retention_in_days = 0
}

resource "aws_lambda_function" "docx" {
  function_name = var.lambda_docx
  memory_size   = 2048
  role          = aws_iam_role.lambda_docx.arn
  timeout       = 900
  image_uri     = "${var.account}.dkr.ecr.${var.region}.amazonaws.com/ats:latest"
  package_type  = "Image"
  #environment_variables = var.env_vars
  environment {
    variables = {
      MPLCONFIGDIR = var.mpl
      WEBHOOK_URL  = var.webhook
      BUCKET       = aws_s3_bucket.download.id
      TIMEOUT      = var.docx_timeout
    }
  }
  image_config {
    command = [
      "ats.docx_handler",
    ]
    entry_point = []
  }
}

resource "aws_lambda_function" "transcribe" {
  function_name = var.lambda_ts
  layers        = []
  memory_size   = 128
  tags          = {}
  role          = aws_iam_role.lambda_transcribe.arn
  timeout       = 30
  image_uri     = "${var.account}.dkr.ecr.${var.region}.amazonaws.com/ats:latest"
  package_type  = "Image"
  environment {
    variables = {
      WEBHOOK_URL = var.webhook
      BUCKET      = aws_s3_bucket.download.id
    }
  }
  image_config {
    command = [
      "ats.transcribe_handler",
    ]
    entry_point = []
  }
}

resource "aws_iam_role_policy_attachment" "function_policy_attachment" {
  role       = aws_iam_role.lambda_docx.id
  policy_arn = aws_iam_policy.lambda_docx.arn
}

resource "aws_iam_role" "lambda_transcribe" {
  name = "${local.prefix}-transcribe-docx-role"
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

resource "aws_iam_policy" "lambda_transcribe" {
  name = "${local.prefix}-lambda-transcribe-policy"
  policy = jsonencode(
    {
      "Version" : "2012-10-17",
      "Statement" : [
        {
          "Sid" : "VisualEditor0",
          "Effect" : "Allow",
          "Action" : "logs:CreateLogGroup",
          "Resource" : "arn:aws:logs:us-east-1:${var.account}:*"
        },
        {
          "Sid" : "VisualEditor1",
          "Effect" : "Allow",
          "Action" : [
            "logs:CreateLogStream",
            "logs:PutLogEvents",
            "sqs:DeleteMessage",
            "s3:PutObject",
            "s3:GetObject",
            "transcribe:GetTranscriptionJob",
            "sqs:ReceiveMessage",
            "sqs:GetQueueAttributes",
            "s3:ListBucket"
          ],
          "Resource" : [
            "arn:aws:transcribe:*:${var.account}:transcription-job/*",
            "arn:aws:logs:us-east-1:${var.account}:log-group:/aws/lambda/audio-to-ts:*",
            aws_sqs_queue.audio_to_transcribe.arn,
            "${aws_s3_bucket.download.arn}/*",
            aws_s3_bucket.download.arn,
            "${aws_s3_bucket.upload.arn}/*",
            aws_s3_bucket.upload.arn
          ]
        },
        {
          "Sid" : "VisualEditor2",
          "Effect" : "Allow",
          "Action" : "transcribe:StartTranscriptionJob",
          "Resource" : "*"
        }
      ]
    }
  )
}

resource "aws_iam_role_policy_attachment" "function_policy_attachment_lambda" {
  role       = aws_iam_role.lambda_transcribe.id
  policy_arn = aws_iam_policy.lambda_transcribe.arn
}

resource "aws_lambda_event_source_mapping" "upload" {
  event_source_arn = aws_sqs_queue.audio_to_transcribe.arn
  function_name    = aws_lambda_function.transcribe.arn
  batch_size       = 10
  maximum_batching_window_in_seconds = 0
}

resource "aws_lambda_event_source_mapping" "download" {
  event_source_arn = aws_sqs_queue.transcribe_to_docx.arn
  function_name    = aws_lambda_function.docx.arn
  batch_size       = 5
  maximum_batching_window_in_seconds = 60
}