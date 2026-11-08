"""Download datasets/v1/train.jsonl + train.sha256 from object storage and verify the checksum."""
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import s3util  # noqa: E402

c = s3util.client()
out = Path("data/v1")
out.mkdir(parents=True, exist_ok=True)
data = s3util.get_bytes(c, "datasets", "v1/train.jsonl")
expected = s3util.get_bytes(c, "datasets", "v1/train.sha256").decode().split()[0]
actual = hashlib.sha256(data).hexdigest()
if actual != expected:
    sys.exit(f"checksum mismatch: {actual} != {expected}")
(out / "train.jsonl").write_bytes(data)
(out / "train.sha256").write_text(f"{expected}  train.jsonl\n")
print("train.jsonl verified", actual)
