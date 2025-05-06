provider "mgc" {
  region  = var.mgc_region
  api_key = var.mgc_api_key
  object_storage = {
    key_pair = {
      key_id     = var.mgc_keypair_id
      key_secret = var.mgc_keypair_secret
    }
  }
}