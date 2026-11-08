"""Task 7: turn Locust's CSV into the numbers for the report: latency, throughput, error rate, SLO error budget, cost.

    python scripts/report_metrics.py --csv results/loadtest_stats.csv --replicas 2 --cpu 1 --mem-gib 1
"""
import argparse
import csv
import json
import math


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="results/loadtest_stats.csv")
    ap.add_argument("--rate-card", default="data/rate_card.json")
    ap.add_argument("--replicas", type=int, required=True, help="running replicas during the test")
    ap.add_argument("--cpu", type=float, default=1.0, help="CPU limit per replica (vCPU)")
    ap.add_argument("--mem-gib", type=float, default=1.0, help="memory limit per replica (GiB)")
    ap.add_argument("--slo", type=float, default=99.0, help="SLO target: percent of requests that succeed")
    a = ap.parse_args()

    rows = list(csv.DictReader(open(a.csv)))
    r = next(x for x in rows if x["Name"] == "/parse")
    n, fails = int(r["Request Count"]), int(r["Failure Count"])
    rps, p50, p95 = float(r["Requests/s"]), float(r["50%"]), float(r["95%"])
    print(f"requests {n}, failures {fails}, error rate {100 * fails / n:.3f}%")
    print(f"p50 {p50:.0f} ms, p95 {p95:.0f} ms, throughput {rps:.2f} req/s")

    card = json.load(open(a.rate_card))
    hourly = a.replicas * (a.cpu * card["vcpu_hour"] + a.mem_gib * card["gib_memory_hour"])
    per_hour = rps * 3600
    print("\nCost estimate (rate_card.json)")
    print(f"  hourly cost = {a.replicas} replicas x ({a.cpu} vCPU x {card['vcpu_hour']} "
          f"+ {a.mem_gib} GiB x {card['gib_memory_hour']}) = {hourly:.4f} INR/h")
    print(f"  requests per hour = {rps:.2f} req/s x 3600 = {per_hour:.0f}")
    print(f"  cost per 1000 requests = {hourly:.4f} / {per_hour:.0f} x 1000 = {hourly / per_hour * 1000:.4f} INR")

    budget = math.floor(n * (100 - a.slo) / 100)
    print(f"\nSLO: {a.slo}% of requests succeed (window = this load-test run, {n} requests)")
    if budget:
        print(f"  error budget = {n} x {(100 - a.slo) / 100:g} = {budget} failed requests; "
              f"used {fails} ({100 * fails / budget:.0f}% of the budget)")
    else:
        print(f"  error budget < 1 request; failures {fails}")


if __name__ == "__main__":
    main()
