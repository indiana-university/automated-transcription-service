resource "aws_sqs_queue" "audio_to_transcribe" {
  name                              = "${var.prefix}-${var.lambda_ts}-queue"
  content_based_deduplication       = false
  delay_seconds                     = 0
  fifo_queue                        = false
  kms_data_key_reuse_period_seconds = 300
  max_message_size                  = 262144
  message_retention_seconds         = 345600
  receive_wait_time_seconds         = 0
  redrive_policy = jsonencode(
    {
      deadLetterTargetArn = aws_sqs_queue.audio_to_transcribe_dlq.arn
      maxReceiveCount     = 3
    }
  )
  sqs_managed_sse_enabled    = true
  tags                       = {}
  tags_all                   = {}
  visibility_timeout_seconds = 30
}

resource "aws_sqs_queue_policy" "audio_to_transcribe" {
  queue_url = aws_sqs_queue.audio_to_transcribe.id
  policy = jsonencode(
    {
      Id = "example-ID"
      Statement = [
        {
          Action = "SQS:SendMessage"
          Condition = {
            ArnLike = {
              "aws:SourceArn" = aws_s3_bucket.upload.arn
            }
            StringEquals = {
              "aws:SourceAccount" = local.account
            }
          }
          Effect = "Allow"
          Principal = {
            Service = "s3.amazonaws.com"
          }
          Resource = aws_sqs_queue.audio_to_transcribe.arn
          Sid      = "example-statement-ID"
        },
      ]
      Version = "2012-10-17"
    }
  )
}

resource "aws_sqs_queue" "audio_to_transcribe_dlq" {
  name                              = "${var.prefix}-${var.lambda_ts}-dlq"
  content_based_deduplication       = false
  delay_seconds                     = 0
  fifo_queue                        = false
  kms_data_key_reuse_period_seconds = 300
  max_message_size                  = 262144
  message_retention_seconds         = 345600
  receive_wait_time_seconds         = 0
  sqs_managed_sse_enabled           = true
  tags                              = {}
  tags_all                          = {}
  visibility_timeout_seconds        = 30
}

resource "aws_sqs_queue_policy" "audio_to_transcribe_dlq" {
  queue_url = aws_sqs_queue.audio_to_transcribe_dlq.id
  policy = jsonencode(
    {
      Id = "__default_policy_ID"
      Statement = [
        {
          Action = "SQS:*"
          Effect = "Allow"
          Principal = {
            AWS = "arn:aws:iam::${local.account}:root"
          }
          Resource = aws_sqs_queue.audio_to_transcribe_dlq.arn
          Sid      = "__owner_statement"
        },
      ]
      Version = "2008-10-17"
    }
  )
}

resource "aws_s3_bucket_notification" "upload_notification" {
  bucket = aws_s3_bucket.upload.id

  queue {
    queue_arn = aws_sqs_queue.audio_to_transcribe.arn
    id        = "audio-to-ts-queue-event"
    events    = ["s3:ObjectCreated:*"]
  }
}