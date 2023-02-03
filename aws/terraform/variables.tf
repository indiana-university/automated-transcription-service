variable "config" {
  description = "path to config file"
  type        = list(string)

}

variable "credentials" {
  description = "path to credentials file"
  type        = list(string)

}

variable "profile" {
  description = "AWS profile to use"
  type        = string
}

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
}

variable "prefix" {
  description = "prefix for bucket names"
  type        = string
}

variable "transcribe_queue" {
  description = "Name of Transcribe-to-docx queue"
  type        = string
}

variable "audio_queue" {
  description = "Name of Audio-to-Transcribe queue"
  type        = string
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

variable "upload" {
  description = "upload bucket"
  type = string
}

variable "download" {
  description = "download bucket"
  type = string
}