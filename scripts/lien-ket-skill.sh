#!/bin/sh
# Đã thay bằng scripts/sync_ai_workspace.py (đồng bộ agent, skill, lệnh giữa Claude và Gemini). Giữ file này để lệnh cũ vẫn chạy.
set -e
cd "$(dirname "$0")/.."
exec python3 scripts/sync_ai_workspace.py "$@"
