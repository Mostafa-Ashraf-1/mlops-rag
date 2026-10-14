output "mlflow_bucket_name" {
  description = "Provisioned S3 bucket for MLflow artifacts"
  value       = aws_s3_bucket.mlflow_artifacts.bucket
}

output "dvc_bucket_name" {
  description = "Provisioned S3 bucket for DVC remote storage"
  value       = aws_s3_bucket.dvc_storage.bucket
}

output "s3_endpoint" {
  description = "Endpoint URL used for S3 storage"
  value       = var.s3_endpoint
}