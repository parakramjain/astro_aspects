from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import boto3
from botocore.exceptions import ClientError


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

    s3 = boto3.client("s3")

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
    except ClientError as e:
        raise RuntimeError(f"S3 upload failed: s3://{target.bucket}/{target.key}") from e


# ---- usage ----
if __name__ == "__main__":
    report_path = "/astro_aspects/output/daily_report.pdf"
    target = S3Target(bucket="my-astro-reports", key="reports/daily/2026-02-21/daily_report.pdf")
    upload_file_to_s3(report_path, target, content_type="application/pdf", sse="AES256")
    print(f"Uploaded to s3://{target.bucket}/{target.key}")
