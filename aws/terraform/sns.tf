module "sns_topic" {
  source  = "terraform-aws-modules/sns/aws"

  name  = "${var.prefix}-notifications"

  tags = local.tags
}