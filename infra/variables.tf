variable "s3_endpoint" {
  type        = string
  description = "MinIO / S3 endpoint URL"
  default     = "http://localhost:9000"
}

variable "aws_region" {
  type        = string
  description = "AWS region identifier"
  default     = "us-east-1"
}

variable "minio_access_key" {
  type        = string
  description = "MinIO access key"
  default     = "minioadmin"
}

variable "minio_secret_key" {
  type        = string
  description = "MinIO secret key"
  default     = "minioadminpassword"
  sensitive   = true
}

variable "mlflow_bucket_name" {
  type        = string
  description = "Bucket name for MLflow artifacts"
  default     = "mlflow"
}

variable "dvc_bucket_name" {
  type        = string
  description = "Bucket name for DVC remote storage"
  default     = "prodml-dvc"
}