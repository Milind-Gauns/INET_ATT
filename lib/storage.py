import os
import streamlit as st
import boto3

def _s3_cfg():
    return st.secrets.get("s3", {})

def _use_s3():
    return bool(_s3_cfg().get("endpoint"))

def put_bytes(key: str, data: bytes, content_type="application/pdf") -> str:
    if _use_s3():
        s = _s3_cfg()
        client = boto3.client(
            "s3",
            endpoint_url=("https://" if s.get("secure", True) else "http://") + s["endpoint"],
            aws_access_key_id=s["access_key"],
            aws_secret_access_key=s["secret_key"],
            region_name=s.get("region", "auto"),
        )
        client.put_object(Bucket=s.get("bucket", "payslips"), Key=key, Body=data, ContentType=content_type)
        return f"s3://{s.get('bucket','payslips')}/{key}"
    # local fallback
    path = os.path.join("payslips", key.replace("/", os.sep))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)
    return path

def presigned_url(key: str, expires=3600) -> str | None:
    if _use_s3():
        s = _s3_cfg()
        client = boto3.client(
            "s3",
            endpoint_url=("https://" if s.get("secure", True) else "http://") + s["endpoint"],
            aws_access_key_id=s["access_key"],
            aws_secret_access_key=s["secret_key"],
            region_name=s.get("region", "auto"),
        )
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": s.get("bucket", "payslips"), "Key": key},
            ExpiresIn=expires,
        )
    return None
