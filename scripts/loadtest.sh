#!/usr/bin/env bash
# Standard load test (the same command is used for assessment). Usage: scripts/loadtest.sh [name] [run-time]
set -uo pipefail
NAME=${1:-loadtest}; RUNTIME=${2:-2m}
mkdir -p results
LOADTEST_HEADERS_OUT=results/${NAME}_headers.json \
locust -f tools/locustfile.py --headless --users 4 --spawn-rate 4 --run-time "$RUNTIME" \
       --host http://localhost:8080 --csv "results/$NAME" 2>&1 | tee "results/${NAME}_locust.log"
exit 0   # locust exits 1 if any request failed; that is normal, read the numbers
