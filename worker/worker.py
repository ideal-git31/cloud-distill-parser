"""Teacher-labelling worker.

Reads SHARD_INDEX (from 0) and SHARD_COUNT. Takes the commands whose line number (from 0) leaves
remainder SHARD_INDEX when divided by SHARD_COUNT, asks the teacher for each, and writes
datasets/teacher/shard-<SHARD_INDEX>.jsonl:  {"id", "text", "teacher_raw"}.
The shard object is checkpointed every CHECKPOINT records so a restarted Pod resumes where it stopped.
"""
import json
import os
import sys

from common import s3util
from worker import teacher

CHECKPOINT = 25


def select_shard(lines, shard_index, shard_count):
    """Yield parsed records whose 0-based line number % shard_count == shard_index."""
    if not (shard_count > 0 and 0 <= shard_index < shard_count):
        raise ValueError("need 0 <= SHARD_INDEX < SHARD_COUNT")
    for n, line in enumerate(lines):
        if n % shard_count == shard_index and line.strip():
            yield json.loads(line)


def dump(records):
    return "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records).encode("utf-8")


def main():
    idx = int(os.environ["SHARD_INDEX"])
    cnt = int(os.environ["SHARD_COUNT"])
    c = s3util.client()
    pool = s3util.get_bytes(c, "datasets", "commands_pool.jsonl").decode("utf-8").splitlines()
    todo = list(select_shard(pool, idx, cnt))
    key = f"teacher/shard-{idx}.jsonl"

    done = []
    if s3util.object_exists(c, "datasets", key):  # resume after a restart
        done = [json.loads(x) for x in s3util.get_bytes(c, "datasets", key).decode("utf-8").splitlines() if x.strip()]
    finished = {r["id"] for r in done}
    template = teacher.load_prompt()
    print(f"shard {idx}/{cnt}: {len(todo)} commands, {len(finished)} already done", flush=True)

    for n, rec in enumerate(todo, 1):
        if rec["id"] in finished:
            continue
        raw = teacher.ask_teacher(rec["text"], template)
        done.append({"id": rec["id"], "text": rec["text"], "teacher_raw": raw})
        if len(done) % CHECKPOINT == 0:
            s3util.put_bytes(c, "datasets", key, dump(done))
            print(f"  checkpoint: {len(done)}/{len(todo)}", flush=True)

    done.sort(key=lambda r: r["id"])
    s3util.put_bytes(c, "datasets", key, dump(done))
    print(f"shard {idx} finished: {len(done)} records -> datasets/{key}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
