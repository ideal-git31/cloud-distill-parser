"""Upload a packaged model directory to object storage: s3://models/<version>/ (weights are never put in Git).

    python training/upload_model.py --dir training/out/v1 --version v1
Needs S3_ENDPOINT, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY in the environment.
The release archive itself is not uploaded; the service downloads the individual files.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import s3util  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--version", required=True)
    a = ap.parse_args()
    c = s3util.client()
    s3util.ensure_bucket(c, "models")
    n = 0
    for p in sorted(Path(a.dir).iterdir()):
        if p.is_file() and not p.name.endswith(".tar.gz"):
            c.upload_file(str(p), "models", f"{a.version}/{p.name}")
            n += 1
    print(f"uploaded {n} files to s3://models/{a.version}/")
    for k in s3util.list_keys(c, "models", f"{a.version}/"):
        print("  ", k)


if __name__ == "__main__":
    main()
