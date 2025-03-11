resource "aws_cloudwatch_event_rule" "transcribe_job_rule" {
  name        = "${var.prefix}-capture-transcribe-job-end"
  description = "Capture when Transcribe job ends"
  event_pattern = jsonencode({
    "detail": {
      "TranscriptionJobStatus": ["COMPLETED", "FAILED"]
    },
    "detail-type": ["Transcribe Job State Change"],
    "source": ["aws.transcribe"]
  })
  state = "ENABLED"
}

resource "aws_iam_role" "eventbridge_role" {
  name = "${var.prefix}-eventbridge-stepfunction-role"
  assume_role_policy = jsonencode({
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {
          "Service": "events.amazonaws.com"
        },
        "Action": "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_policy" "eventbridge_policy" {
  name   = "${var.prefix}-eventbridge-stepfunction-policy"
  policy = jsonencode({
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": "states:StartExecution",
        "Resource": module.step_function.state_machine_arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "eventbridge_role_policy_attachment" {
  role       = aws_iam_role.eventbridge_role.name
  policy_arn = aws_iam_policy.eventbridge_policy.arn
}

resource "aws_cloudwatch_event_target" "trigger_step_function" {
  rule      = aws_cloudwatch_event_rule.transcribe_job_rule.name
  target_id = "trigger-ats-postprocessing"
  arn       = module.step_function.state_machine_arn
  role_arn  = aws_iam_role.eventbridge_role.arn
}
