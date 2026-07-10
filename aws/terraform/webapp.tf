###############################################################################
# Static hosting for the Storage Browser web app (opt-in)
#
# A private S3 bucket holds the built React bundle; CloudFront serves it over
# HTTPS. No servers. Gated behind var.enable_storage_browser.
###############################################################################

locals {
  # Origins allowed to call the upload/download buckets directly from the browser.
  # The CloudFront URL is always included; a custom domain and any dev origins
  # (e.g. http://localhost:5173) are added when configured.
  webapp_origins = compact(concat(
    var.webapp_domain != "" ? ["https://${var.webapp_domain}"] : [],
    [for d in aws_cloudfront_distribution.webapp[*].domain_name : "https://${d}"],
    var.webapp_dev_origins,
  ))
}

resource "aws_s3_bucket" "webapp" {
  count         = local.storage_browser_count
  bucket_prefix = "${var.prefix}-webapp-"
  tags          = { Project = "ATS" }
}

resource "aws_s3_bucket_public_access_block" "webapp" {
  count  = local.storage_browser_count
  bucket = aws_s3_bucket.webapp[0].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# CloudFront reaches the private bucket via Origin Access Control (SigV4).
resource "aws_cloudfront_origin_access_control" "webapp" {
  count                             = local.storage_browser_count
  name                              = "${var.prefix}-webapp"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

data "aws_cloudfront_cache_policy" "optimized" {
  name = "Managed-CachingOptimized"
}

resource "aws_cloudfront_distribution" "webapp" {
  count               = local.storage_browser_count
  enabled             = true
  default_root_object = "index.html"
  comment             = "${var.prefix} Storage Browser"
  aliases             = var.webapp_domain != "" ? [var.webapp_domain] : []
  price_class         = "PriceClass_100"

  origin {
    domain_name              = aws_s3_bucket.webapp[0].bucket_regional_domain_name
    origin_id                = "webapp-s3"
    origin_access_control_id = aws_cloudfront_origin_access_control.webapp[0].id
  }

  default_cache_behavior {
    target_origin_id       = "webapp-s3"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    cache_policy_id        = data.aws_cloudfront_cache_policy.optimized.id
  }

  # Single-page app: route unknown paths back to index.html.
  custom_error_response {
    error_code         = 403
    response_code      = 200
    response_page_path = "/index.html"
  }
  custom_error_response {
    error_code         = 404
    response_code      = 200
    response_page_path = "/index.html"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = var.webapp_domain == "" ? true : null
    acm_certificate_arn            = var.webapp_domain != "" ? var.acm_certificate_arn : null
    ssl_support_method             = var.webapp_domain != "" ? "sni-only" : null
    minimum_protocol_version       = var.webapp_domain != "" ? "TLSv1.2_2021" : null
  }

  tags = { Project = "ATS" }
}

# Allow only this CloudFront distribution to read the web bucket.
data "aws_iam_policy_document" "webapp_bucket" {
  count = local.storage_browser_count

  statement {
    sid       = "AllowCloudFrontOAC"
    effect    = "Allow"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.webapp[0].arn}/*"]

    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.webapp[0].arn]
    }
  }
}

resource "aws_s3_bucket_policy" "webapp" {
  count  = local.storage_browser_count
  bucket = aws_s3_bucket.webapp[0].id
  policy = data.aws_iam_policy_document.webapp_bucket[0].json
}

###############################################################################
# CORS on the upload/download buckets so the browser can transfer files directly.
# The buckets stay fully private; CORS only whitelists the app's origin(s).
###############################################################################

resource "aws_s3_bucket_cors_configuration" "upload" {
  count  = local.storage_browser_count
  bucket = aws_s3_bucket.upload.id

  cors_rule {
    allowed_origins = local.webapp_origins
    allowed_methods = ["GET", "PUT", "POST", "DELETE", "HEAD"]
    allowed_headers = ["*"]
    expose_headers  = ["ETag", "x-amz-request-id", "x-amz-version-id"]
    max_age_seconds = 3000
  }
}

resource "aws_s3_bucket_cors_configuration" "download" {
  count  = local.storage_browser_count
  bucket = aws_s3_bucket.download.id

  cors_rule {
    allowed_origins = local.webapp_origins
    allowed_methods = ["GET", "HEAD"]
    allowed_headers = ["*"]
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}
