variable "location" {
  type        = string
  default     = "eastus"
  description = "Azure region supporting Speech and Functions Flex Consumption."
}
variable "prefix" {
  type        = string
  default     = "ats"
  description = "Resource name prefix."
}
variable "retention_days" {
  type        = number
  default     = 30
  description = "Uploaded and generated file retention."
}
variable "document_title" {
  type        = string
  default     = "Transcription Results"
  description = "DOCX title."
}
variable "confidence_score" {
  type        = number
  default     = 90
  description = "Highlight words below this percentage."
  validation {
    condition     = var.confidence_score >= 50 && var.confidence_score <= 100
    error_message = "confidence_score must be between 50 and 100."
  }
}

variable "speech_locales" {
  type        = list(string)
  default     = ["en-US"]
  description = "Language candidates; first is the fallback locale."
  validation {
    condition     = length(var.speech_locales) >= 1 && length(var.speech_locales) <= 10
    error_message = "Provide 1-10 locales."
  }
}

variable "max_speakers" {
  type        = number
  default     = 10
  description = "Maximum diarized speakers."
  validation {
    condition     = var.max_speakers >= 2 && var.max_speakers <= 35
    error_message = "max_speakers must be 2-35."
  }
}

variable "teams_webhook" {
  type        = string
  default     = ""
  sensitive   = true
  description = "Optional Teams workflow webhook."
}
variable "slack_webhook" {
  type        = string
  default     = ""
  sensitive   = true
  description = "Optional Slack webhook."
}
