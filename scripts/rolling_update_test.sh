#!/usr/bin/env bash
# Task 4.5: rolling update v1 -> v2 and rollback while the load test runs.
set -uo pipefail
mkdir -p results
D="kubectl -n app"
LOG=results/rolling_update_commands.log
{
echo "== start load test (5m) in background"; scripts/loadtest.sh rolling 5m > /dev/null 2>&1 &
LT=$!
sleep 30
echo "== $(date +%T) switch to v2";   $D set env deployment/parser MODEL_VERSION=v2 MODEL_URI=s3://models/v2/
$D rollout status deployment/parser --timeout=300s
echo "== headers after update";       curl -si -X POST localhost:8080/parse -H 'content-type: application/json' -d '{"text":"what is the weather in london"}' | grep -i -E '^HTTP|x-model|x-served'
sleep 30
echo "== $(date +%T) rollback";       $D rollout undo deployment/parser
$D rollout status deployment/parser --timeout=300s
echo "== headers after rollback";     curl -si -X POST localhost:8080/parse -H 'content-type: application/json' -d '{"text":"what is the weather in london"}' | grep -i -E '^HTTP|x-model|x-served'
wait $LT
echo "== per-version counts:"; cat results/rolling_headers.json
} 2>&1 | tee $LOG
