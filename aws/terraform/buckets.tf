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