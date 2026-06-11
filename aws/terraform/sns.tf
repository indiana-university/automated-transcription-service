module "sns_topic" {
  source  = "terraform-aws-modules/sns/aws"
  version = "7.1.0"

  name = "${var.prefix}-notifications"

  tags = local.tags
}