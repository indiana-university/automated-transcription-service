output "upload_bucket_name" {
  value = aws_s3_bucket.upload.bucket
}

output "download_bucket_name" {
  value = aws_s3_bucket.download.bucket
}

output "dynamodb_table_name" {
  value = module.dynamodb_table.dynamodb_table_id
}