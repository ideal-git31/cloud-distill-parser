#!/usr/bin/env bash
# Task 4.6: delete one Pod while the load test runs; show the replica count recovers.
set -uo pipefail
mkdir -p results
D="kubectl -n app"
{
$D scale deployment/parser --replicas=2; $D rollout status deployment/parser
$D delete hpa parser --ignore-not-found      # keep the replica count fixed for this test
scripts/loadtest.sh recovery 3m > /dev/null 2>&1 &
LT=$!
sleep 30
echo "== before:"; $D get pods
VICTIM=$($D get pods -o jsonpath='{.items[0].metadata.name}')
echo "== $(date +%T) deleting $VICTIM"; $D delete pod "$VICTIM"
for i in $(seq 1 24); do sleep 5; echo "-- $(date +%T)"; $D get pods; done | tail -40
$D rollout status deployment/parser --timeout=300s
wait $LT
echo "== ready replicas:"; $D get deployment parser
} 2>&1 | tee results/recovery_commands.log
echo "Re-create the HPA afterwards:  kubectl apply -f k8s/30-app.yaml"
