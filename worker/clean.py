"""Clean the teacher shards and write datasets/v1/train.jsonl + train.sha256.

Rejection rules (applied in this order; a record is counted under the FIRST rule it breaks):
  (a) reply is not valid JSON
  (b) keys are not exactly intent, date, time, place
  (c) intent is not one of the eight
  (d) a slot value is neither null nor text that appears in the command
Then duplicates: among the records that passed (a)-(d), a command text that already appeared is
dropped; the record with the smallest id is kept. So  input = a + b + c + d + duplicates + kept.
Records are kept in id order, so the output (and its SHA-256) is deterministic.

Usage:
  python -m worker.clean                      # reads/writes the object store (S3_ENDPOINT + AWS_* env)
  python -m worker.clean --local DIR --pool data/commands_pool.jsonl --out data/v1
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

INTENTS = {
    "alarm_set", "alarm_query", "calendar_set", "calendar_query",
    "calendar_remove", "weather_query", "datetime_query", "recommendation_events",
}
KEYS = {"intent", "date", "time", "place"}
SLOTS = ("date", "time", "place")


def classify(rec):
    """Return the first rejection rule ('a'..'d') the record breaks, or None if it is fine."""
    try:
        obj = json.loads(rec["teacher_raw"].strip())
    except (ValueError, TypeError, AttributeError):
        return "a"
    if not isinstance(obj, dict) or set(obj) != KEYS:
        return "b"
    if not isinstance(obj["intent"], str) or obj["intent"] not in INTENTS:
        return "c"
    for k in SLOTS:
        v = obj[k]
        if v is not None and not (isinstance(v, str) and v in rec["text"]):
            return "d"
    return None


def clean_records(records):
    records = sorted(records, key=lambda r: r["id"])
    counts = {"input": len(records), "a_invalid_json": 0, "b_wrong_keys": 0,
              "c_bad_intent": 0, "d_bad_slot": 0, "duplicates": 0, "kept": 0}
    names = {"a": "a_invalid_json", "b": "b_wrong_keys", "c": "c_bad_intent", "d": "d_bad_slot"}
    kept, seen = [], set()
    for rec in records:
        rule = classify(rec)
        if rule:
            counts[names[rule]] += 1
        elif rec["text"] in seen:
            counts["duplicates"] += 1
        else:
            seen.add(rec["text"])
            kept.append(rec)
    counts["kept"] = len(kept)
    assert counts["input"] == sum(counts[k] for k in counts if k != "input"), "counts do not add up"
    return kept, counts


def check_coverage(pool_ids, shard_ids):
    """Every command id must appear in exactly one shard output: no gaps, no repeats."""
    from collections import Counter
    c = Counter(shard_ids)
    repeats = sorted(i for i, n in c.items() if n > 1)
    gaps = sorted(set(pool_ids) - set(c))
    extra = sorted(set(c) - set(pool_ids))
    return gaps, repeats, extra


def serialise(kept):
    rows = [{"id": r["id"], "text": r["text"], "teacher_raw": r["teacher_raw"]} for r in kept]
    return "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows).encode("utf-8")


def read_jsonl_bytes(data):
    return [json.loads(x) for x in data.decode("utf-8").splitlines() if x.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--local", help="directory with shard-*.jsonl instead of the object store")
    ap.add_argument("--pool", default="data/commands_pool.jsonl", help="(local mode) commands pool")
    ap.add_argument("--out", default="data/v1", help="(local mode) output directory")
    ap.add_argument("--counts-out", default="results/cleaning_counts.json")
    ap.add_argument(
        "--subset-size",
        type=int,
        default=None,
        help="Validate coverage against the first N commands in the pool instead of the full pool",
    )
    a = ap.parse_args()

    if a.local:
        shards = sorted(Path(a.local).glob("shard-*.jsonl"))
        records = [r for p in shards for r in read_jsonl_bytes(p.read_bytes())]
        pool_ids = [r["id"] for r in read_jsonl_bytes(Path(a.pool).read_bytes())]
    else:
        from common import s3util
        c = s3util.client()
        keys = [k for k in s3util.list_keys(c, "datasets", "teacher/") if k.endswith(".jsonl")]
        records = [r for k in keys for r in read_jsonl_bytes(s3util.get_bytes(c, "datasets", k))]
        pool_ids = [r["id"] for r in read_jsonl_bytes(s3util.get_bytes(c, "datasets", "commands_pool.jsonl"))]

    if a.subset_size is not None:
        if not 1 <= a.subset_size <= len(pool_ids):
            sys.exit("--subset-size must be between 1 and the pool size")
        expected_ids = pool_ids[:a.subset_size]
        scope = f"first {a.subset_size} commands of {len(pool_ids)}"
    else:
        expected_ids = pool_ids
        scope = f"full pool ({len(pool_ids)} commands)"

    gaps, repeats, extra = check_coverage(expected_ids, [r["id"] for r in records])
    print(
        f"shard coverage ({scope}): {len(records)} records, "
        f"gaps={len(gaps)} repeats={len(repeats)} unknown={len(extra)}"
    )
    if gaps or repeats or extra:
        sys.exit(f"shards are inconsistent: gaps={gaps[:5]} repeats={repeats[:5]} unknown={extra[:5]}")

    kept, counts = clean_records(records)
    data = serialise(kept)
    digest = hashlib.sha256(data).hexdigest()
    checksum_line = f"{digest}  train.jsonl\n".encode()

    if a.local:
        out = Path(a.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / "train.jsonl").write_bytes(data)
        (out / "train.sha256").write_bytes(checksum_line)
    else:
        s3util.put_bytes(c, "datasets", "v1/train.jsonl", data)
        s3util.put_bytes(c, "datasets", "v1/train.sha256", checksum_line)

    Path(a.counts_out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.counts_out).write_text(json.dumps(counts, indent=2) + "\n")
    print(json.dumps(counts, indent=2))
    print(f"sha256 {digest}")


if __name__ == "__main__":
    main()
