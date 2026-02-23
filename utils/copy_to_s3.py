from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import boto3
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError
from dotenv import load_dotenv

load_dotenv()

AWS_REGION = os.getenv("AWS_REGION", "us-east-2")
S3_BUCKET = os.getenv("S3_BUCKET", "")
S3_PREFIX = os.getenv("S3_PREFIX", "reports").strip("/")


@dataclass(frozen=True)
class S3Target:
    bucket: str
    key: str  # e.g. "reports/daily/2026-02-21/report.pdf"


def upload_file_to_s3(
    file_path: str,
    target: S3Target,
    content_type: Optional[str] = None,
    kms_key_id: Optional[str] = None,
    sse: Optional[str] = "AES256",  # or "aws:kms"
) -> None:
    """
    Inputs:
      - file_path: local path to the generated report
      - target.bucket: S3 bucket
      - target.key: S3 object key (path in bucket)
    Output:
      - uploads file to S3 (raises on failure)
    Assumptions:
      - AWS credentials are available via env/instance-role/profile
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Report file not found: {file_path}")

    s3 = boto3.client("s3", region_name=AWS_REGION)

    extra_args = {}
    if content_type:
        extra_args["ContentType"] = content_type

    # Server-side encryption (recommended)
    if sse:
        extra_args["ServerSideEncryption"] = sse
    if sse == "aws:kms" and kms_key_id:
        extra_args["SSEKMSKeyId"] = kms_key_id

    try:
        s3.upload_file(file_path, target.bucket, target.key, ExtraArgs=extra_args or None)
    except (NoCredentialsError, PartialCredentialsError) as e:
        raise RuntimeError(
            "AWS credentials not found. Configure one of: "
            "(1) AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY (+ AWS_SESSION_TOKEN if needed), "
            "(2) AWS_PROFILE, or (3) IAM role attached to runtime."
        ) from e
    except ClientError as e:
        raise RuntimeError(f"S3 upload failed: s3://{target.bucket}/{target.key}") from e


# ---- usage ----
if __name__ == "__main__":
    if not S3_BUCKET:
        raise RuntimeError("S3_BUCKET is required in .env")

    report_path = os.path.join("output", "daily_report.pdf")
    target = S3Target(bucket=S3_BUCKET, key=f"{S3_PREFIX}/daily/2026-02-21/daily_report.pdf")
    upload_file_to_s3(report_path, target, content_type="application/pdf", sse="AES256")
    print(f"Uploaded to s3://{target.bucket}/{target.key}")
