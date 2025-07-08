resource "aws_s3_bucket" "download" {
  bucket_prefix = "${var.prefix}-download-"
}

resource "aws_s3_bucket" "upload" {
  bucket_prefix = "${var.prefix}-upload-"
}

resource "aws_s3_bucket_public_access_block" "dblock" {
  bucket = aws_s3_bucket.download.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "ublock" {
  bucket = aws_s3_bucket.upload.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "download-lifecycle" {
  bucket = aws_s3_bucket.download.id
  rule {
    id = "${var.prefix}-download-lifecycle-expire"

    expiration {
      days = var.retention_days
    }

    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "upload-lifecycle" {
  bucket = aws_s3_bucket.upload.id
  rule {
    id = "${var.prefix}-upload-lifecycle-expire"

    expiration {
      days = var.retention_days
    }

    status = "Enabled"
  }
}
