# Secrets Manager resources for webhook URLs

resource "aws_secretsmanager_secret" "teams_webhook" {
  count                   = var.teams_notification ? 1 : 0
  name                    = "${var.prefix}-teams-webhook"
  description             = "Teams webhook URL for ATS notifications"
  recovery_window_in_days = 7

  tags = {
    Project = "ATS"
  }
}

resource "aws_secretsmanager_secret_version" "teams_webhook" {
  count         = var.teams_notification ? 1 : 0
  secret_id     = aws_secretsmanager_secret.teams_webhook[0].id
  secret_string = var.teams_webhook
}

resource "aws_secretsmanager_secret" "slack_webhook" {
  count                   = var.slack_notification ? 1 : 0
  name                    = "${var.prefix}-slack-webhook"
  description             = "Slack webhook URL for ATS notifications"
  recovery_window_in_days = 7

  tags = {
    Project = "ATS"
  }
}

resource "aws_secretsmanager_secret_version" "slack_webhook" {
  count         = var.slack_notification ? 1 : 0
  secret_id     = aws_secretsmanager_secret.slack_webhook[0].id
  secret_string = var.slack_webhook
}