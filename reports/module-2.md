# Module 2 Lab Report: MLOps Core — Tracking, Versioning & Automation

## 1. Continuous Training (CT) Decision Table

| Trigger Type | What Triggers It | Implemented In | Action Taken |
| :--- | :--- | :--- | :--- |
| **Schedule** | Weekly cron job (`0 0 * * 0`) | Module 2 | Re-evaluates retrieval against latest court amendments and checks benchmark baseline. |
| **Data Drift** | Significant shift in legal query vocabulary or amendment language | Module 5 | Drift detector fires `repository_dispatch` webhook to initiate candidate re-indexing. |
| **Performance Degradation** | Live RAGAS faithfulness drops below 0.75 in production | Module 5 | Triggers automated canary rollback and launches candidate retraining. |
| **New Labeled Data** | New Civil Code amendment PDF committed via DVC | Module 2 | Rebuilds corpus chunks, updates vector store, and triggers quality gate. |

## 2. Why Production Auto-Promotion is Forbidden

Automatic promotion to `Staging` is safe because staging is an isolated sandbox environment used for smoke tests, load testing, and security evaluation. 

However, **Production requires human approval** because legal AI applications carry high compliance liability: a corrupted text extraction or an unchecked legal hallucination could give legally hazardous advice to citizens or attorneys. A human reviewer must inspect the benchmark metrics, verify repealed article coverage, and confirm legal citations before shifting live user traffic.

## 3. Infrastructure as Code (Terraform Plan)

The storage infrastructure (MinIO S3-compatible buckets `mlflow` and `prodml-dvc`) was provisioned reproducibly with object versioning enabled using Terraform:

- `dvc_bucket_name = "prodml-dvc"`
- `mlflow_bucket_name = "mlflow"`
- `s3_endpoint = "http://localhost:9000"`

State files (`*.tfstate*`) are strictly excluded from Git tracking to protect sensitive credentials and avoid state corruption.