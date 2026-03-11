#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 2 ]; then
  echo "Usage: bash scripts/test_upload_example.sh <TASK_UUID> <IMAGE_PATH>"
  exit 1
fi

TASK_ID="$1"
IMAGE_PATH="$2"

curl -fsS -X POST "http://localhost:8080/api/tasks/$TASK_ID/attachments" \
  -F "file=@${IMAGE_PATH}"
echo
