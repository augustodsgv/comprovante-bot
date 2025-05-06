variable "mgc_api_key" {
  type        = string
  description = "mgc api key"
}

variable "mgc_keypair_id" {
  type        = string
  description = "mgc object key id"
}

variable "mgc_keypair_secret" {
  type        = string
  description = "mgc object key secret"
}

variable "mgc_region" {
  type        = string
  description = "mgc region"
  default     = "br-se1"
}