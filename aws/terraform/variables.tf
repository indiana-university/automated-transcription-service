variable "region" {
  description = "AWS Region to use"
  type        = string
}

variable "mpl" {
  description = "default directory for matplot lib"
  type        = string
}

variable "webhook" {
  description = "teams webhook"
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
}

variable "lambda_ts" {
  description = "name of the lambda function audio-to-ts function"
  type        = string
}

variable "docx_timeout" {
  description = "Timeout for docx lambda function"
  type        = number
}

variable "account" {
  description = "account number"
  type        = string
}

variable "retention_days" {
  description = "Number of days to keep download bucket files"
  type        = number
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