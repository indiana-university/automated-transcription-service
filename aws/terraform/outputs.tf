output "upload_bucket_name" {
  value = aws_s3_bucket.upload.bucket
}

output "download_bucket_name" {
  value = aws_s3_bucket.download.bucket
}

output "dynamodb_table_name" {
  value = module.dynamodb_table.dynamodb_table_id
}

# --- Storage Browser web app (null unless enable_storage_browser = true) ---
# These feed the web app build (see aws/web/.env.template).

output "region" {
  value = var.region
}

output "storage_browser_url" {
  value = one([for d in aws_cloudfront_distribution.webapp[*].domain_name : "https://${coalesce(var.webapp_domain, d)}"])
}

output "cognito_user_pool_id" {
  value = one(aws_cognito_user_pool.ats[*].id)
}

output "cognito_user_pool_client_id" {
  value = one(aws_cognito_user_pool_client.ats[*].id)
}

output "cognito_identity_pool_id" {
  value = one(aws_cognito_identity_pool.ats[*].id)
}

output "cognito_domain" {
  value = one([for d in aws_cognito_user_pool_domain.ats[*].domain : "${d}.auth.${var.region}.amazoncognito.com"])
}

output "oidc_provider_name" {
  value = one(aws_cognito_identity_provider.oidc[*].provider_name)
}

# Give this to the identity-provider team when registering the relying party
# (along with the scopes: openid email profile). They return a client ID and
# secret for the tfvars.
output "oidc_redirect_uri" {
  value = one([for d in aws_cognito_user_pool_domain.ats[*].domain : "https://${d}.auth.${var.region}.amazoncognito.com/oauth2/idpresponse"])
}

output "webapp_bucket_name" {
  value = one(aws_s3_bucket.webapp[*].bucket)
}

output "webapp_cloudfront_distribution_id" {
  value = one(aws_cloudfront_distribution.webapp[*].id)
}
