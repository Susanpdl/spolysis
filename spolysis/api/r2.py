from __future__ import annotations
import boto3
from botocore.config import Config
from api.config import settings

_client = None


def get_r2_client():
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


def generate_upload_url(r2_key: str, content_type: str = "video/mp4", expires_in: int = 300) -> str:
    client = get_r2_client()
    url = client.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.r2_bucket_name,
            "Key": r2_key,
            "ContentType": content_type,
        },
        ExpiresIn=expires_in,
    )
    return url


def get_public_url(r2_key: str) -> str:
    return f"{settings.r2_public_url.rstrip('/')}/{r2_key}"
