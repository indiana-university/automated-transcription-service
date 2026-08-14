variable "location" {
  type        = string
  default     = "eastus"
  description = "Azure region supporting Speech and Functions Flex Consumption."
  validation {
    condition     = can(regex("^[a-z0-9]+$", var.location))
    error_message = "location must be a lowercase Azure region name such as eastus or westus2."
  }
}
variable "prefix" {
  type        = string
  default     = "ats"
  description = "Resource name prefix."
  validation {
    condition     = can(regex("^[a-z][a-z0-9]{1,11}$", var.prefix))
    error_message = "prefix must be 2-12 lowercase letters or digits and start with a letter."
  }
}
variable "retention_days" {
  type        = number
  default     = 30
  description = "Uploaded and generated file retention."
  validation {
    condition     = floor(var.retention_days) == var.retention_days && var.retention_days >= 1 && var.retention_days <= 3650
    error_message = "retention_days must be a whole number from 1 through 3650."
  }
}
variable "document_title" {
  type        = string
  default     = "Transcription Results"
  description = "DOCX title."
  validation {
    condition     = length(trimspace(var.document_title)) >= 1 && length(var.document_title) <= 200
    error_message = "document_title must contain 1-200 characters."
  }
}
variable "confidence_score" {
  type        = number
  default     = 90
  description = "Highlight words below this percentage."
  validation {
    condition     = floor(var.confidence_score) == var.confidence_score && var.confidence_score >= 50 && var.confidence_score <= 100
    error_message = "confidence_score must be a whole number from 50 through 100."
  }
}

variable "speech_locales" {
  type        = list(string)
  default     = ["en-US", "es-US", "de-DE"]
  description = "Language-identification candidates; first is the fallback locale."
  validation {
    condition     = length(var.speech_locales) >= 2 && length(var.speech_locales) <= 10
    error_message = "speech_locales must contain 2-10 candidates."
  }
  validation {
    condition     = length(distinct(var.speech_locales)) == length(var.speech_locales)
    error_message = "speech_locales must not contain duplicates."
  }
  validation {
    condition = length(distinct([
      for locale in var.speech_locales : split("-", lower(locale))[0]
    ])) == length(var.speech_locales)
    error_message = "speech_locales must contain only one locale for each language."
  }
  validation {
    condition = alltrue([
      for locale in var.speech_locales :
      locale == trimspace(locale) && can(regex("^[a-z]{2,3}(-[A-Za-z0-9]{2,8})+$", locale))
    ])
    error_message = "Each speech locale must be a trimmed BCP-47-style value such as en-US or zh-Hans-CN."
  }
}

variable "speech_language_identification_mode" {
  type        = string
  default     = "Continuous"
  description = "Speech language-identification mode."
  validation {
    condition     = contains(["Continuous", "Single"], var.speech_language_identification_mode)
    error_message = "speech_language_identification_mode must be Continuous or Single."
  }
}

variable "max_speakers" {
  type        = number
  default     = 10
  description = "Maximum diarized speakers."
  validation {
    condition     = floor(var.max_speakers) == var.max_speakers && var.max_speakers >= 2 && var.max_speakers <= 35
    error_message = "max_speakers must be a whole number from 2 through 35."
  }
}

variable "blob_data_contributor_group_object_ids" {
  type        = set(string)
  default     = []
  description = "Microsoft Entra group object IDs granted read/write upload/download blob access and read access to all tables in the ATS storage account."
  validation {
    condition = alltrue([
      for object_id in var.blob_data_contributor_group_object_ids :
      can(regex("^[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}$", object_id))
    ])
    error_message = "Each blob data contributor group object ID must be a GUID."
  }
}

variable "teams_webhook" {
  type        = string
  default     = ""
  sensitive   = true
  description = "Optional Teams workflow webhook."
  validation {
    condition     = var.teams_webhook == "" || can(regex("^https://[^ ]+$", var.teams_webhook))
    error_message = "teams_webhook must be empty or an HTTPS URL without spaces."
  }
}
variable "slack_webhook" {
  type        = string
  default     = ""
  sensitive   = true
  description = "Optional Slack webhook."
  validation {
    condition     = var.slack_webhook == "" || can(regex("^https://[^ ]+$", var.slack_webhook))
    error_message = "slack_webhook must be empty or an HTTPS URL without spaces."
  }
}
