#!/usr/bin/env python3
"""
One-shot private R2 bucket setup: create bucket and set upload CORS.
Run from repo root: python data/scripts/setup_r2.py
"""

from __future__ import annotations
import os
import sys
from pathlib import Path
import boto3
from botocore.exceptions import ClientError

# Load .env manually so we don't need python-dotenv
env_path = Path(__file__).parent.parent.parent / ".env"
for line in env_path.read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"'))

ACCOUNT_ID = os.environ["R2_ACCOUNT_ID"]
ACCESS_KEY = os.environ["R2_ACCESS_KEY_ID"]
SECRET_KEY = os.environ["R2_SECRET_ACCESS_KEY"]
BUCKET = os.environ.get("R2_BUCKET_NAME", "spolysis")
ENDPOINT = f"https://{ACCOUNT_ID}.r2.cloudflarestorage.com"

s3 = boto3.client(
    "s3",
    endpoint_url=ENDPOINT,
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
    region_name="auto",
)

# 1. Create bucket (idempotent)
print(f"Creating bucket '{BUCKET}' ...")
try:
    s3.create_bucket(Bucket=BUCKET)
    print("  Created.")
except ClientError as e:
    code = e.response["Error"]["Code"]
    if code in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
        print("  Already exists - OK.")
    else:
        print(f"  ERROR: {e}")
        sys.exit(1)

# 2. CORS - allow the app and Fly.io backend to upload/read
print("Setting CORS ...")
cors = {
    "CORSRules": [
        {
            "AllowedOrigins": ["*"],
            "AllowedMethods": ["GET", "PUT", "POST", "DELETE", "HEAD"],
            "AllowedHeaders": ["*"],
            "MaxAgeSeconds": 3600,
        }
    ]
}
s3.put_bucket_cors(Bucket=BUCKET, CORSConfiguration=cors)
print("  Done.")

# 3. Verify bucket is accessible
print("Verifying bucket access ...")
resp = s3.list_objects_v2(Bucket=BUCKET, MaxKeys=1)
print(f"  OK - bucket has {resp.get('KeyCount', 0)} object(s) so far.")

print()
print("R2 setup complete.")
print(f"  Bucket:   {BUCKET}")
print(f"  Endpoint: {ENDPOINT}")
print("Keep public access disabled. The API issues signed upload and download URLs.")
