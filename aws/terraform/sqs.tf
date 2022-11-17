resource "aws_sqs_queue" "transcribe_to_docx" {
  name = "transcribe-to-docx-queue"
}

resource "aws_sqs_queue_policy" "test" {
  queue_url = aws_sqs_queue.transcribe_to_docx.id

  policy = <<POLICY
{
  "Version": "2012-10-17",
  "Id": "sqspolicy",
  "Statement": [
    {
      "Sid": "First",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "sqs:SendMessage",
      "Resource": "${aws_sqs_queue.transcribe_to_docx.arn}",
      "Condition": {
        "ArnEquals": {
          "aws:SourceArn": "${aws_cloudwatch_event_rule.transcribe.arn}"
        }
      }
    }
  ]
}
POLICY
}