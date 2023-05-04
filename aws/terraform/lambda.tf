resource "aws_iam_role" "lambda_docx" {
  name = "${var.lambda_docx}-role"
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
  name = "${var.lambda_docx}-policy"
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
            "sqs:ReceiveMessage",
            "sqs:GetQueueAttributes",
            "sqs:DeleteMessage",
          ],
          "Resource" : [
            "arn:aws:transcribe:*:${var.account}:transcription-job/*",
            "${aws_cloudwatch_log_group.docx.arn}:*",
            aws_sqs_queue.transcribe_to_docx.arn,
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
  name              = "/aws/lambda/${var.lambda_docx}"
  retention_in_days = 0
}

resource "aws_cloudwatch_log_group" "transcribe" {
  name              = "/aws/lambda/${var.lambda_ts}"
  retention_in_days = 0
}

resource "aws_lambda_function" "docx" {
  depends_on = [
    aws_cloudwatch_log_group.docx
  ]
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
      CONFIDENCE   = var.confidence_score
    }
  }
  image_config {
    command = [
      "transcribe_to_docx.lambda_handler",
    ]
    entry_point = []
  }
}

resource "aws_lambda_function" "transcribe" {
  depends_on = [
    aws_cloudwatch_log_group.transcribe
  ]
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
      "audio_to_transcribe.lambda_handler",
    ]
    entry_point = []
  }
}

resource "aws_iam_role_policy_attachment" "docx" {
  role       = aws_iam_role.lambda_docx.id
  policy_arn = aws_iam_policy.lambda_docx.arn
}

resource "aws_iam_role" "lambda_transcribe" {
  name = "${var.lambda_ts}-role"
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
  name = "${var.lambda_ts}-policy"
  policy = jsonencode(
    {
      "Version" : "2012-10-17",
      "Statement" : [
        {
          "Sid" : "VisualEditor0",
          "Effect" : "Allow",
          "Action" : "logs:CreateLogGroup",
          "Resource" : "arn:aws:logs:${var.region}:${var.account}:*"
        },
        {
          "Sid" : "VisualEditor1",
          "Effect" : "Allow",
          "Action" : [
            "logs:CreateLogStream",
            "logs:PutLogEvents",
            "s3:PutObject",
            "s3:GetObject",
            "s3:ListBucket",
            "transcribe:GetTranscriptionJob",
            "sqs:ReceiveMessage",
            "sqs:DeleteMessage",
            "sqs:GetQueueAttributes",
          ],
          "Resource" : [
            "arn:aws:transcribe:*:${var.account}:transcription-job/*",
            "${aws_cloudwatch_log_group.transcribe.arn}:*",
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

resource "aws_iam_role_policy_attachment" "transcribe" {
  role       = aws_iam_role.lambda_transcribe.id
  policy_arn = aws_iam_policy.lambda_transcribe.arn
}

resource "aws_lambda_event_source_mapping" "upload" {
  event_source_arn                   = aws_sqs_queue.audio_to_transcribe.arn
  function_name                      = aws_lambda_function.transcribe.arn
  batch_size                         = 10
  maximum_batching_window_in_seconds = 0
}

resource "aws_lambda_event_source_mapping" "download" {
  event_source_arn                   = aws_sqs_queue.transcribe_to_docx.arn
  function_name                      = aws_lambda_function.docx.arn
  batch_size                         = 5
  maximum_batching_window_in_seconds = 60
}