"""S3-compatible object storage (SeaweedFS locally, S3 in production).

All buckets except `cms-public` are private. Object keys are always server-generated;
user-supplied filenames are never used as keys.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
from enum import StrEnum
from functools import lru_cache
from typing import TYPE_CHECKING

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import get_settings

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client


class Bucket(StrEnum):
    PRESCRIPTIONS = "prescriptions"
    REPORTS = "reports"
    INVOICES = "invoices"
    ATTACHMENTS = "attachments"
    CMS_PUBLIC = "cms-public"


PRIVATE_BUCKETS = tuple(b for b in Bucket if b is not Bucket.CMS_PUBLIC)


def bucket_name(bucket: Bucket) -> str:
    return f"{get_settings().s3_bucket_prefix}-{bucket.value}"


@lru_cache
def _client() -> S3Client:
    s = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=s.s3_endpoint_url,
        region_name=s.s3_region,
        aws_access_key_id=s.s3_access_key.get_secret_value() or None,
        aws_secret_access_key=s.s3_secret_key.get_secret_value() or None,
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
            connect_timeout=3,
            read_timeout=10,
            retries={"max_attempts": 2},
        ),
    )


async def put_object(bucket: Bucket, key: str, data: bytes, content_type: str) -> None:
    extra: dict[str, str] = {}
    sse = get_settings().s3_server_side_encryption
    if sse and bucket is not Bucket.CMS_PUBLIC:
        extra["ServerSideEncryption"] = sse
    await asyncio.to_thread(
        _client().put_object,
        Bucket=bucket_name(bucket),
        Key=key,
        Body=data,
        ContentType=content_type,
        **extra,  # type: ignore[arg-type]
    )


async def presigned_get_url(bucket: Bucket, key: str, *, expires_seconds: int = 300) -> str:
    return await asyncio.to_thread(
        _client().generate_presigned_url,
        "get_object",
        Params={"Bucket": bucket_name(bucket), "Key": key},
        ExpiresIn=expires_seconds,
    )


def ensure_buckets() -> list[str]:
    """Create any missing buckets (idempotent). Private by default; CMS assets get a
    public-read policy. In production, buckets are usually provisioned by infrastructure
    code and this only verifies they exist."""
    client = _client()
    existing = {b["Name"] for b in client.list_buckets().get("Buckets", [])}
    created = []
    for bucket in Bucket:
        name = bucket_name(bucket)
        if name not in existing:
            region = get_settings().s3_region
            if region == "us-east-1":
                client.create_bucket(Bucket=name)
            else:  # AWS requires an explicit location outside us-east-1
                client.create_bucket(
                    Bucket=name,
                    # Region comes from config; S3 itself rejects unknown values.
                    CreateBucketConfiguration={"LocationConstraint": region},  # type: ignore[typeddict-item]
                )
            created.append(name)
        if bucket is Bucket.CMS_PUBLIC:
            policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": "*",
                        "Action": ["s3:GetObject"],
                        "Resource": [f"arn:aws:s3:::{name}/*"],
                    }
                ],
            }
            # Some S3-compatible servers lack bucket policies; then serve CMS assets via a CDN.
            with contextlib.suppress(ClientError):
                client.put_bucket_policy(Bucket=name, Policy=json.dumps(policy))
    return created


async def ping_storage() -> bool:
    await asyncio.to_thread(_client().head_bucket, Bucket=bucket_name(Bucket.ATTACHMENTS))
    return True
