#!/usr/bin/env bash
set -euo pipefail

REQ="requirements.txt"

if [ ! -f "$REQ" ]; then
  echo "ERROR: $REQ not found"
  exit 1
fi

if grep -qiE '^minio([=<>!~].*)?$' "$REQ"; then
  echo "OK: minio already present in $REQ"
else
  echo 'minio==7.2.15' >> "$REQ"
  echo "OK: minio added to $REQ"
fi
