variable "region" {
  description = "AWS Region to use"
  type        = string
  default     = "us-east-1"
}

variable "mpl" {
  description = "default directory for matplot lib"
  type        = string
  default     = "/tmp"
}

variable "teams_webhook" {
  description = "Teams webhook"
  type        = string
  default     = "DISABLED"
}

variable "slack_webhook" {
  description = "Slack webhook"
  type        = string
  default     = "DISABLED"
}

variable "prefix" {
  description = "prefix for bucket names"
  type        = string
  default     = "ats"
}

variable "lambda_docx" {
  description = "name of the lambda ts-to-docx function"
  type        = string
  default     = "transcribe-to-docx"
}

variable "lambda_ts" {
  description = "name of the lambda function audio-to-ts function"
  type        = string
  default     = "audio-to-transcribe"
}

variable "docx_timeout" {
  description = "Timeout for docx lambda function"
  type        = number
  default     = 300000 # 5 minutes in milliseconds
}

variable "account" {
  description = "account number"
  type        = string
  default     = ""
}

variable "retention_days" {
  description = "Number of days to keep download bucket files"
  type        = number
  default     = 30
}

variable "confidence_score" {
  description = "Lower threshold in percent for which not to highlight confidence score. Needs to be between 50-100"
  type        = number
  default     = 90
}

variable "docx_max_duration" {
  description = "Max transcription duration in seconds that transcribe_to_docx will process before issuing a failure"
  type        = number
  default     = 13150
}

variable "teams_notification" {
  description = "Whether to create the SNS teams_notification Lambda and subscribe it to the SNS topic"
  type        = bool
  default     = false
}

variable "slack_notification" {
  description = "Whether to create the SNS slack_notification Lambda and subscribe it to the SNS topic"
  type        = bool
  default     = false
}

variable "python_version" {
  description = "Python version to use for the Lambda functions. Supported versions: 3.13 or later"
  type        = string
  default     = "3.13"
}

variable "document_title" {
  description = "Title for the generated document. This will be used in the DOCX file header."
  type        = string
  default     = "Transcription Results"
}

# --- Storage Browser web app (optional, off by default) ---

variable "enable_storage_browser" {
  description = "Deploy the Storage Browser web app along with its Cognito identity and CloudFront hosting resources."
  type        = bool
  default     = false
}

variable "oidc_issuer_url" {
  description = "Issuer URL of the institution's OpenID Connect identity provider (discovery document at <issuer>/.well-known/openid-configuration). Required when enable_storage_browser is true — OIDC single sign-on is the only implemented sign-in path."
  type        = string
  default     = ""
}

variable "oidc_client_id" {
  description = "Client ID issued when registering this app with the OIDC identity provider. Required when enable_storage_browser is true."
  type        = string
  default     = ""
}

variable "oidc_client_secret" {
  description = "Client secret issued when registering this app with the OIDC identity provider. Required when enable_storage_browser is true. Used only between Cognito and the IdP; stored in Terraform state, so protect the state file."
  type        = string
  default     = ""
  sensitive   = true
}

variable "oidc_provider_name" {
  description = "Display name for the OIDC identity provider in Cognito (also used by the web app to start sign-in)."
  type        = string
  default     = "SSO"
}

variable "cognito_domain_prefix" {
  description = "Globally unique (per region) prefix for the Cognito hosted domain that handles the sign-in redirect. Blank derives '<prefix>-storage-browser'."
  type        = string
  default     = ""
}

variable "webapp_domain" {
  description = "Optional custom domain for the Storage Browser web app (e.g. transcribe.example.edu). Blank uses the default CloudFront URL. Requires acm_certificate_arn when set."
  type        = string
  default     = ""
}

variable "acm_certificate_arn" {
  description = "ARN of an ACM certificate in us-east-1 for webapp_domain. Required only when webapp_domain is set."
  type        = string
  default     = ""
}

variable "webapp_dev_origins" {
  description = "Extra CORS origins allowed to access the buckets, for local development (e.g. [\"http://localhost:5173\"])."
  type        = list(string)
  default     = []
}
