#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://localhost:8000}"

curl -sS "$BASE_URL/health" | jq '.'
curl -sS "$BASE_URL/reference/status" | jq '.'
