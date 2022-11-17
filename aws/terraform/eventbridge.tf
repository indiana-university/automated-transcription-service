resource "aws_cloudwatch_event_rule" "transcribe" {
  name        = "capture-transcribe-job-end"
  description = "Capture when Transcribe job ends"

  event_pattern = <<EOF
{
    "source": [
        "aws.transcribe"
    ],
    "detail-type": [
        "Transcribe Job State Change"
    ],
    "detail": {
        "TranscriptionJobStatus": [
            "COMPLETED",
            "FAILED"
        ]
    }
}
EOF
}

resource "aws_cloudwatch_event_target" "sqs" {
  rule      = aws_cloudwatch_event_rule.transcribe.name
  target_id = "SendToSQS"
  arn       = aws_sqs_queue.transcribe_to_docx.arn
}