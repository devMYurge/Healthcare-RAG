#!/usr/bin/env bash
set -euo pipefail

# Wait for backend health endpoint and write metadata to a status file
# Usage: ./scripts/wait_for_backend.sh [URL] [TIMEOUT_SECONDS]
# Defaults: URL=http://localhost:8000/api/health, TIMEOUT_SECONDS=60

URL=${1:-http://localhost:8000/api/health}
TIMEOUT=${2:-60}
OUT_DIR=${3:-deploy/status}
OUT_FILE="$OUT_DIR/backend_health.json"

mkdir -p "$OUT_DIR"

echo "Waiting up to $TIMEOUT seconds for backend at $URL"
START=$(date +%s)
END=$((START + TIMEOUT))
SLEEP=1
STATUS=1
RESPONSE=""

while [ $(date +%s) -le $END ]; do
  if RESPONSE=$(curl -sS --max-time 5 "$URL" 2>/dev/null); then
    # got response
  # Create an ISO timestamp (portable) and write JSON using Python to avoid
  # dependency on GNU date or jq on macOS
  TIMESTAMP=$(python3 - <<'PY'
import datetime
print(datetime.datetime.utcnow().replace(microsecond=0).isoformat() + 'Z')
PY
)
  python3 - <<PY > "$OUT_FILE"
import json
resp = json.loads(r'''$RESPONSE''')
out = {"status": "healthy", "response": resp, "timestamp": "$TIMESTAMP"}
print(json.dumps(out))
PY
    echo "Backend is healthy. Wrote metadata to $OUT_FILE"
    STATUS=0
    break
  else
    sleep $SLEEP
  fi
done

if [ $STATUS -ne 0 ]; then
  TIMESTAMP=$(python3 - <<'PY'
import datetime
print(datetime.datetime.utcnow().replace(microsecond=0).isoformat() + 'Z')
PY
)
  python3 - <<PY > "$OUT_FILE"
import json
print(json.dumps({"status":"unreachable","timestamp":"$TIMESTAMP"}))
PY
  echo "Timeout reached; backend not healthy. Wrote status to $OUT_FILE"
fi

exit $STATUS
