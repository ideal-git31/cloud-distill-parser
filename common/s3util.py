"""Small S3 helpers for SeaweedFS (S3-compatible). Credentials come from the environment only."""
import os
from pathlib import Path


def client(endpoint=None):
    import boto3  # imported lazily so unit tests do not need boto3
    from botocore.config import Config

    return boto3.client(
        "s3",
        endpoint_url=endpoint or os.environ["S3_ENDPOINT"],
        aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
        region_name="us-east-1",
        config=Config(s3={"addressing_style": "path"}, retries={"max_attempts": 5, "mode": "standard"}),
    )


def parse_uri(uri):
    """'s3://models/v1/' -> ('models', 'v1/')"""
    if not uri.startswith("s3://"):
        raise ValueError(f"not an s3 uri: {uri}")
    bucket, _, prefix = uri[5:].partition("/")
    if prefix and not prefix.endswith("/"):
        prefix += "/"
    return bucket, prefix


def ensure_bucket(c, bucket):
    existing = {b["Name"] for b in c.list_buckets().get("Buckets", [])}
    if bucket not in existing:
        c.create_bucket(Bucket=bucket)


def object_exists(c, bucket, key):
    try:
        c.head_object(Bucket=bucket, Key=key)
        return True
    except Exception:
        return False


def get_bytes(c, bucket, key):
    return c.get_object(Bucket=bucket, Key=key)["Body"].read()


def put_bytes(c, bucket, key, data):
    c.put_object(Bucket=bucket, Key=key, Body=data)


def list_keys(c, bucket, prefix=""):
    keys = []
    for page in c.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefix):
        keys.extend(o["Key"] for o in page.get("Contents", []))
    return sorted(keys)


def download_prefix(c, bucket, prefix, dest):
    """Download every object under prefix into dest (flat, by file name). Returns the file count."""
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    n = 0
    for key in list_keys(c, bucket, prefix):
        name = key[len(prefix):]
        if not name or name.endswith("/"):
            continue
        target = dest / name
        target.parent.mkdir(parents=True, exist_ok=True)
        c.download_file(bucket, key, str(target))
        n += 1
    return n


def upload_dir(c, local_dir, bucket, prefix, skip=()):
    local_dir = Path(local_dir)
    n = 0
    for p in sorted(local_dir.rglob("*")):
        if p.is_file() and p.name not in skip:
            c.upload_file(str(p), bucket, prefix + p.relative_to(local_dir).as_posix())
            n += 1
    return n
