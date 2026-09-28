#!/bin/bash
# Mỗi lượt Lighthouse chạy trên Chrome headless với profile MỚI (cache trình duyệt lạnh).
# Server Cloud Run đã làm ấm trước bằng curl. LH 13.5: desktop=--preset=desktop, mobile=--form-factor=mobile (slow-4G sim mặc định).
set -u
CD=/Users/dangthiduyen/Downloads/loc/scratchpad/qa-perf-baseline
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PORT=9224
OUT="$1"; URL="$2"; FLAGS="$3"

PROFILE="$(mktemp -d /tmp/lh-prof.XXXXXX)"
"$CHROME" --headless=new --remote-debugging-port=$PORT --user-data-dir="$PROFILE" \
  --no-first-run --no-default-browser-check --disable-background-networking about:blank >/dev/null 2>&1 &
CHPID=$!
for i in $(seq 1 40); do
  curl -s --max-time 2 "http://localhost:$PORT/json/version" >/dev/null 2>&1 && break
  sleep 0.25
done
cd "$CD"
./node_modules/.bin/lighthouse "$URL" --port=$PORT $FLAGS --only-categories=performance \
  --output=json --output-path="$OUT" --quiet 2>/dev/null
RC=$?
kill $CHPID >/dev/null 2>&1
wait $CHPID >/dev/null 2>&1
rm -rf "$PROFILE"
exit $RC
