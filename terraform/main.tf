terraform {
  required_providers {
    mgc = {
      source  = "MagaluCloud/mgc"
      version = "0.33.0"
    }
  }
}

# Object storage
resource "mgc_object_storage_buckets" "comprovante-bot" {
  bucket            = "comprovante-bot"
  bucket_is_prefix  = false
  enable_versioning = false
  private = true
}

# TODO: create VM