#!/usr/bin/env bash
# Download model-<v>.tar.gz from the GitHub Release, verify it against the committed models/<v>/model.sha256,
# unpack it and upload the files to s3://models/<v>/ (so a fresh clone gets the same model without retraining).
# Usage: scripts/seed_models.sh <github-repo> [v1 v2]
set -euo pipefail
REPO=${1:?usage: seed_models.sh owner/repo [versions...]}; shift || true
VERSIONS=${*:-v1 v2}
PY=${PYTHON:-python3}
for v in $VERSIONS; do
  if [[ ! -f models/$v/model.sha256 ]]; then echo "skip $v: models/$v/model.sha256 not committed yet"; continue; fi
  tmp=$(mktemp -d)
  url="https://github.com/$REPO/releases/download/model-$v/model-$v.tar.gz"
  echo "downloading $url"
  if ! curl -fsSL -o "$tmp/model-$v.tar.gz" "$url"; then
    # private repository? fall back to the authenticated GitHub CLI
    if ! gh release download "model-$v" --repo "$REPO" --pattern "model-$v.tar.gz" --dir "$tmp" 2>/dev/null; then
      echo "skip $v: release asset not found"; continue
    fi
  fi
  expected=$(cut -d' ' -f1 models/$v/model.sha256)
  actual=$($PY -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" "$tmp/model-$v.tar.gz")
  [[ "$expected" == "$actual" ]] || { echo "checksum mismatch for $v" >&2; exit 1; }
  mkdir -p "$tmp/files" && tar -xzf "$tmp/model-$v.tar.gz" -C "$tmp/files"
  cp models/$v/model.sha256 "$tmp/files/model.sha256"
  $PY training/upload_model.py --dir "$tmp/files" --version "$v"
  rm -rf "$tmp"
done
