import io
import os


def get_minio_client():
    from minio import Minio

    endpoint = os.getenv("MINIO_ENDPOINT", "minio:9000")
    access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    secure = os.getenv("MINIO_SECURE", "false").lower() == "true"

    return Minio(
        endpoint=endpoint,
        access_key=access_key,
        secret_key=secret_key,
        secure=secure,
    )


def get_bucket_name() -> str:
    return os.getenv("MINIO_BUCKET", "itcs")


def ensure_bucket():
    client = get_minio_client()
    bucket = get_bucket_name()
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)
    return client, bucket


def upload_bytes(object_key: str, data: bytes, content_type: str):
    client, bucket = ensure_bucket()
    client.put_object(
        bucket_name=bucket,
        object_name=object_key,
        data=io.BytesIO(data),
        length=len(data),
        content_type=content_type,
    )
    return {"bucket": bucket, "object_key": object_key}


def presigned_get_url(object_key: str, expires_seconds: int = 3600) -> str:
    from datetime import timedelta

    client = get_minio_client()
    bucket = get_bucket_name()
    return client.presigned_get_object(bucket, object_key, expires=timedelta(seconds=expires_seconds))
