provider "aws" {
  region                      = var.aws_region
  access_key                  = var.minio_access_key
  secret_key                  = var.minio_secret_key
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true
  s3_use_path_style           = true

  endpoints {
    s3 = var.s3_endpoint
  }
}

# 1. S3 Bucket for MLflow Artifacts with Versioning
resource "aws_s3_bucket" "mlflow_artifacts" {
  bucket        = var.mlflow_bucket_name
  force_destroy = true
}

resource "aws_s3_bucket_versioning" "mlflow_versioning" {
  bucket = aws_s3_bucket.mlflow_artifacts.id
  versioning_configuration {
    status = "Enabled"
  }
}

# 2. S3 Bucket for DVC Remote Storage with Versioning
resource "aws_s3_bucket" "dvc_storage" {
  bucket        = var.dvc_bucket_name
  force_destroy = true
}

resource "aws_s3_bucket_versioning" "dvc_versioning" {
  bucket = aws_s3_bucket.dvc_storage.id
  versioning_configuration {
    status = "Enabled"
  }
}