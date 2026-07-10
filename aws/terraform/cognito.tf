###############################################################################
# Identity + authorization for the Storage Browser web app (opt-in)
#
# Everything in this file and webapp.tf is gated behind var.enable_storage_browser
# so the default `terraform apply` is unchanged for existing deployments.
#
# Model: sign-in is SAML single sign-on ONLY. The Cognito user pool is purely a
# broker to the institution's SAML 2.0 identity provider — it manages no
# passwords and sends no invitations. Users are provisioned just-in-time on
# first login, and WHO may log in is controlled at the IdP (register the
# service provider so that only the authorized group can authenticate).
# Every authenticated user receives temporary AWS credentials scoped by one
# IAM role to just the two project buckets.
#
# Cognito-managed sign-in (native accounts + email invitations) is possible
# but deliberately not implemented.
###############################################################################

locals {
  storage_browser_count = var.enable_storage_browser ? 1 : 0
  cognito_domain        = coalesce(var.cognito_domain_prefix, "${var.prefix}-storage-browser")
}

# --- User pool: pure SAML broker -------------------------------------------------

resource "aws_cognito_user_pool" "ats" {
  count = local.storage_browser_count
  name  = "${var.prefix}-storage-browser"

  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]

  # No native sign-in exists (the app client only offers the SAML provider);
  # blocking self sign-up is defense in depth.
  admin_create_user_config {
    allow_admin_create_user_only = true
  }

  tags = { Project = "ATS" }
}

# Hosted domain that handles the SAML redirect flow.
resource "aws_cognito_user_pool_domain" "ats" {
  count        = local.storage_browser_count
  domain       = local.cognito_domain
  user_pool_id = aws_cognito_user_pool.ats[0].id
}

# The institution's SAML 2.0 identity provider.
resource "aws_cognito_identity_provider" "saml" {
  count         = local.storage_browser_count
  user_pool_id  = aws_cognito_user_pool.ats[0].id
  provider_name = var.saml_provider_name
  provider_type = "SAML"

  provider_details = {
    MetadataURL = var.saml_metadata_url
  }

  attribute_mapping = {
    email = var.saml_email_attribute
  }

  lifecycle {
    precondition {
      condition     = var.saml_metadata_url != ""
      error_message = "enable_storage_browser requires saml_metadata_url (the IdP's SAML metadata URL)."
    }
  }
}

# Public SPA client (no secret — the app runs in the browser). SAML is the only
# supported identity provider, so there is no username/password path.
resource "aws_cognito_user_pool_client" "ats" {
  count        = local.storage_browser_count
  name         = "${var.prefix}-storage-browser"
  user_pool_id = aws_cognito_user_pool.ats[0].id

  generate_secret               = false
  prevent_user_existence_errors = "ENABLED"

  supported_identity_providers         = [aws_cognito_identity_provider.saml[0].provider_name]
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid", "email", "profile"]
  callback_urls                        = local.webapp_origins
  logout_urls                          = local.webapp_origins

  explicit_auth_flows = ["ALLOW_REFRESH_TOKEN_AUTH"]
}

# --- Identity pool: exchanges a sign-in for temporary AWS credentials -----------

resource "aws_cognito_identity_pool" "ats" {
  count                            = local.storage_browser_count
  identity_pool_name               = "${var.prefix}-storage-browser"
  allow_unauthenticated_identities = false

  cognito_identity_providers {
    client_id               = aws_cognito_user_pool_client.ats[0].id
    provider_name           = aws_cognito_user_pool.ats[0].endpoint
    server_side_token_check = true
  }
}

# Anyone the IdP allows to authenticate gets the bucket-scoped role below.
# Access control (who may sign in at all) lives at the IdP.
resource "aws_cognito_identity_pool_roles_attachment" "ats" {
  count            = local.storage_browser_count
  identity_pool_id = aws_cognito_identity_pool.ats[0].id

  roles = {
    authenticated = aws_iam_role.storage_browser_authorized[0].arn
  }
}

# --- IAM role assumed via the identity pool --------------------------------------

# Trust policy: only this identity pool's authenticated users.
data "aws_iam_policy_document" "cognito_assume" {
  count = local.storage_browser_count

  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = ["cognito-identity.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "cognito-identity.amazonaws.com:aud"
      values   = [aws_cognito_identity_pool.ats[0].id]
    }

    condition {
      test     = "ForAnyValue:StringLike"
      variable = "cognito-identity.amazonaws.com:amr"
      values   = ["authenticated"]
    }
  }
}

# Read/write the upload bucket, read-only the download bucket — nothing else.
resource "aws_iam_role" "storage_browser_authorized" {
  count              = local.storage_browser_count
  name               = "${var.prefix}-storage-browser-authorized"
  assume_role_policy = data.aws_iam_policy_document.cognito_assume[0].json
  tags               = { Project = "ATS" }
}

data "aws_iam_policy_document" "storage_browser_authorized" {
  count = local.storage_browser_count

  statement {
    sid    = "ListBuckets"
    effect = "Allow"
    actions = [
      "s3:ListBucket",
      "s3:GetBucketLocation",
      "s3:ListBucketMultipartUploads",
    ]
    resources = [
      aws_s3_bucket.upload.arn,
      aws_s3_bucket.download.arn,
    ]
  }

  statement {
    sid    = "UploadReadWrite"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:AbortMultipartUpload",
      "s3:ListMultipartUploadParts",
    ]
    resources = ["${aws_s3_bucket.upload.arn}/*"]
  }

  statement {
    sid       = "DownloadReadOnly"
    effect    = "Allow"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.download.arn}/*"]
  }
}

resource "aws_iam_role_policy" "storage_browser_authorized" {
  count  = local.storage_browser_count
  name   = "${var.prefix}-storage-browser-authorized"
  role   = aws_iam_role.storage_browser_authorized[0].id
  policy = data.aws_iam_policy_document.storage_browser_authorized[0].json
}
