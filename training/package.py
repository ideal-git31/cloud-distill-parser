"""Package a trained model directory: deterministic tar.gz + model.sha256 + files.sha256.

model.sha256  = SHA-256 of the release archive  model-<version>.tar.gz   (the GitHub Release asset)
files.sha256  = SHA-256 of every file inside the archive
"""
import gzip
import hashlib
import io
import sys
import tarfile
from pathlib import Path

SKIP = {"model.sha256", "files.sha256"}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def model_files(model_dir):
    return [p for p in sorted(Path(model_dir).iterdir()) if p.is_file() and p.name not in SKIP and not p.name.endswith(".tar.gz")]


def package(model_dir, version):
    model_dir = Path(model_dir)
    files = model_files(model_dir)
    (model_dir / "files.sha256").write_text("".join(f"{sha256_file(p)}  {p.name}\n" for p in files))
    archive = model_dir / f"model-{version}.tar.gz"
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as gz:
        with tarfile.open(fileobj=gz, mode="w") as tar:
            for p in files + [model_dir / "files.sha256"]:
                info = tar.gettarinfo(str(p), arcname=p.name)
                info.uid = info.gid = 0
                info.uname = info.gname = ""
                info.mtime = 0
                with open(p, "rb") as f:
                    tar.addfile(info, f)
    archive.write_bytes(buf.getvalue())
    digest = sha256_file(archive)
    (model_dir / "model.sha256").write_text(f"{digest}  {archive.name}\n")
    return archive, digest


if __name__ == "__main__":
    d, v = sys.argv[1], sys.argv[2]
    a, h = package(d, v)
    print(a, h)
