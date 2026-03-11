#!/bin/sh
set -eu

echo "[minio-init] configure alias"
mc alias set local http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"

echo "[minio-init] create bucket if missing: $MINIO_BUCKET"
mc mb --ignore-existing "local/$MINIO_BUCKET"

echo "[minio-init] allow downloads via presigned urls"
mc anonymous set private "local/$MINIO_BUCKET" || true

echo "[minio-init] done"
