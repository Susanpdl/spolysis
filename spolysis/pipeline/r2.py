from __future__ import annotations
import boto3
import json
import io
import numpy as np
from botocore.config import Config
from pipeline.config import settings

_client = None


def get_client():
    global _client
    if _client is None:
        _client = boto3.client(
            "s3",
            endpoint_url=f"https://{settings.r2_account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=settings.r2_access_key_id,
            aws_secret_access_key=settings.r2_secret_access_key,
            config=Config(signature_version="s3v4"),
            region_name="auto",
        )
    return _client


def upload_file(local_path: str, r2_key: str, content_type: str = "application/octet-stream") -> None:
    get_client().upload_file(local_path, settings.r2_bucket_name, r2_key, ExtraArgs={"ContentType": content_type})


def download_file(r2_key: str, local_path: str) -> None:
    get_client().download_file(settings.r2_bucket_name, r2_key, local_path)


def put_json(r2_key: str, data: dict | list) -> None:
    body = json.dumps(data).encode()
    get_client().put_object(Bucket=settings.r2_bucket_name, Key=r2_key, Body=body, ContentType="application/json")


def get_json(r2_key: str) -> dict | list:
    obj = get_client().get_object(Bucket=settings.r2_bucket_name, Key=r2_key)
    return json.loads(obj["Body"].read())


def put_npz(r2_key: str, **arrays: np.ndarray) -> None:
    buf = io.BytesIO()
    np.savez_compressed(buf, **arrays)
    buf.seek(0)
    get_client().put_object(Bucket=settings.r2_bucket_name, Key=r2_key, Body=buf.read(), ContentType="application/octet-stream")


def get_npz(r2_key: str) -> dict[str, np.ndarray]:
    obj = get_client().get_object(Bucket=settings.r2_bucket_name, Key=r2_key)
    buf = io.BytesIO(obj["Body"].read())
    return dict(np.load(buf))


def get_public_url(r2_key: str) -> str:
    return f"{settings.r2_public_url.rstrip('/')}/{r2_key}"


def key_exists(r2_key: str) -> bool:
    try:
        get_client().head_object(Bucket=settings.r2_bucket_name, Key=r2_key)
        return True
    except Exception:
        return False
