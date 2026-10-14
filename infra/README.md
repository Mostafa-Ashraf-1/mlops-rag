# Infrastructure as Code (Terraform)

This directory defines the reproducible storage infrastructure (MinIO S3-compatible buckets for MLflow artifacts and DVC remote storage) using Terraform.

## Why State Files Must Never Be Committed

Terraform state files (`terraform.tfstate`) contain a direct, comprehensive mapping of real-world infrastructure IDs, configurations, and sensitive metadata (such as database passwords, access keys, and connection strings in plaintext). Committing state files to Git leads to immediate security leaks, merge conflicts when multiple engineers apply changes simultaneously, and race conditions that corrupt infrastructure state.

## What Remote State Backends Solve

Remote backends (such as AWS S3 with DynamoDB locking, HashiCorp HCP Terraform, or Google Cloud Storage) solve this by:
1. **Centralized Single Source of Truth:** Storing the state file securely off-machine with encryption-at-rest.
2. **State Locking:** Preventing concurrent runs from applying contradictory infrastructure changes simultaneously.
3. **Auditability & Role-Based Access:** Enforcing least-privilege access to infrastructure state without exposing credentials in git commits.