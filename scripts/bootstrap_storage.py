"""Create the buckets `datasets` and `models` and upload commands_pool.jsonl to datasets."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import s3util  # noqa: E402

c = s3util.client()
for b in ("datasets", "models"):
    s3util.ensure_bucket(c, b)
c.upload_file("data/commands_pool.jsonl", "datasets", "commands_pool.jsonl")
print("buckets:", [b["Name"] for b in c.list_buckets()["Buckets"]])
print("datasets/:", s3util.list_keys(c, "datasets"))
