#!/usr/bin/env bash
# Task 3: run the image with 1 CPU / 1 GiB, send 50 sequential requests, report peak memory.
# Needs: the cluster up (S3 port-forward on :8333), the image cmd-parser:1.0 built, models/v1 uploaded.
set -euo pipefail
source .secrets/s3.env
scripts/pf.sh start
mkdir -p results
docker rm -f parser-memtest >/dev/null 2>&1 || true
docker run -d --name parser-memtest --cpus=1 --memory=1g --memory-swap=1g -p 8001:8000 \
  --add-host=host.docker.internal:host-gateway \
  -e MODEL_URI=s3://models/v1/ -e MODEL_VERSION=v1 -e S3_ENDPOINT=http://host.docker.internal:8333 -e MAX_NEW_TOKENS=64 \
  -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY cmd-parser:1.0 >/dev/null
for _ in $(seq 1 120); do [[ $(curl -s -o /dev/null -w '%{http_code}' localhost:8001/readyz) == 200 ]] && break; sleep 2; done
{
  echo "# docker run --cpus=1 --memory=1g ...   ($(date -u +%FT%TZ))"
  peak=0
  for i in $(seq 1 50); do
    code=$(curl -s -o /dev/null -w '%{http_code}' -X POST localhost:8001/parse -H 'content-type: application/json' -d '{"text":"set an alarm for seven am tomorrow"}')
    mem=$(docker stats --no-stream --format '{{.MemUsage}}' parser-memtest | cut -d/ -f1)
    echo "request $i -> HTTP $code, memory $mem"
  done
  echo "--- docker stats (final):"; docker stats --no-stream parser-memtest
  echo "--- OOMKilled? $(docker inspect -f '{{.State.OOMKilled}}' parser-memtest)"
  echo "--- peak memory (cgroup):"; docker exec parser-memtest sh -c 'cat /sys/fs/cgroup/memory.peak 2>/dev/null || cat /sys/fs/cgroup/memory/memory.max_usage_in_bytes'
} 2>&1 | tee results/memory_test.txt
docker rm -f parser-memtest >/dev/null
