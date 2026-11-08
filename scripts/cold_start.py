"""Task 4.7: delete all Pods, wait until Ready, and report creation->Ready time (3 runs + median)."""
import json
import statistics
import subprocess
import time
from datetime import datetime

NS = "app"


def k(*args):
    return subprocess.run(["kubectl", "-n", NS, *args], capture_output=True, text=True, check=True).stdout


def ts(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").timestamp()


times = []
for run in range(1, 4):
    k("delete", "pods", "--all", "--wait=true")
    time.sleep(3)
    k("rollout", "status", "deployment/parser", "--timeout=300s")
    pods = json.loads(k("get", "pods", "-o", "json"))["items"]
    for p in pods:
        ready = next(c for c in p["status"]["conditions"] if c["type"] == "Ready")
        dt = ts(ready["lastTransitionTime"]) - ts(p["metadata"]["creationTimestamp"])
        times.append(dt)
        print(f"run {run}: {p['metadata']['name']} created->Ready {dt:.0f}s")
        print("   log:", [ln for ln in k("logs", p["metadata"]["name"]).splitlines() if "download" in ln])
print(f"median over {len(times)} pods: {statistics.median(times):.1f}s")
print("(timestamps have 1-second resolution)")
