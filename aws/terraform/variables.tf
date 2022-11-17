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
  default     = "default"
}