import os
from io import BytesIO
from typing import Optional

# Optional S3/MinIO creds (set in Environment or Streamlit Secrets)
S3_BUCKET   = os.getenv("S3_BUCKET")
S3_REGION   = os.getenv("S3_REGION", "auto")
S3_ENDPOINT = os.getenv("S3_ENDPOINT")  # e.g. MinIO/R2 custom endpoint
S3_ACCESS   = os.getenv("S3_ACCESS_KEY")
S3_SECRET   = os.getenv("S3_SECRET_KEY")

def _s3_client():
    if not (S3_BUCKET and S3_ACCESS and S3_SECRET):
        return None
    import boto3
    if S3_ENDPOINT:
        return boto3.client(
            "s3",
            region_name=S3_REGION,
            endpoint_url=S3_ENDPOINT,
            aws_access_key_id=S3_ACCESS,
            aws_secret_access_key=S3_SECRET,
        )
    return boto3.client(
        "s3",
        region_name=S3_REGION,
        aws_access_key_id=S3_ACCESS,
        aws_secret_access_key=S3_SECRET,
    )

def put_bytes(key: str, data: bytes) -> str:
    """
    Upload bytes to S3/MinIO if configured; else write to local ./data storage.
    Returns the object key/path.
    """
    s3 = _s3_client()
    if s3:
        s3.put_object(Bucket=S3_BUCKET, Key=key, Body=data, ACL="private", ContentType="application/pdf")
        return key
    # local fallback (ephemeral on Streamlit Cloud)
    path = os.path.join("data", key)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)
    return path

def presigned_url(key: str, expires: int = 3600) -> Optional[str]:
    """
    Get a temporary URL for S3/MinIO; local fallback returns None.
    """
    s3 = _s3_client()
    if not s3:
        return None
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": S3_BUCKET, "Key": key},
        ExpiresIn=expires,
    )
