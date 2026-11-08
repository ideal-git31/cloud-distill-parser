#!/usr/bin/env bash
# Port-forward the SeaweedFS S3 endpoint to localhost:8333.  Usage: scripts/pf.sh start|stop
set -euo pipefail
PIDFILE=.secrets/pf.pid
mkdir -p .secrets
case "${1:-start}" in
  start)
    if [[ -f $PIDFILE ]] && kill -0 "$(cat $PIDFILE)" 2>/dev/null; then exit 0; fi
    kubectl -n data port-forward svc/seaweedfs 8333:8333 >/dev/null 2>&1 &
    echo $! > $PIDFILE
    for _ in $(seq 1 30); do
      if (echo > /dev/tcp/127.0.0.1/8333) 2>/dev/null; then exit 0; fi
      sleep 1
    done
    echo "port-forward to SeaweedFS did not come up" >&2; exit 1 ;;
  stop)
    if [[ -f $PIDFILE ]]; then kill "$(cat $PIDFILE)" 2>/dev/null || true; rm -f $PIDFILE; fi ;;
esac
