module "dynamodb_table" {
  source  = "terraform-aws-modules/dynamodb-table/aws"
  version = ">= 4.2.0"

  name      = "${var.prefix}-jobs-table"
  hash_key  = "PK"
  range_key = "SK"

  attributes = [
    {
      name = "PK"
      type = "S"
    },
    {
      name = "SK"
      type = "S"
    }
  ]

  billing_mode = "PAY_PER_REQUEST"

  ttl_enabled        = true
  ttl_attribute_name = "TTL"

  point_in_time_recovery_enabled = true
  server_side_encryption_enabled = true

  tags = {
    Project = "ATS"
  }
}