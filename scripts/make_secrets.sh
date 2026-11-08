#!/usr/bin/env bash
# Create the S3 credentials as Kubernetes Secrets. Keys are generated randomly on first run and kept only in
# .secrets/s3.env (git-ignored) and in the cluster. Nothing secret is ever committed.
set -euo pipefail
mkdir -p .secrets
if [[ ! -f .secrets/s3.env ]]; then
  AK="seaweed$(openssl rand -hex 6)"
  SK="$(openssl rand -hex 20)"
  printf 'export AWS_ACCESS_KEY_ID=%s\nexport AWS_SECRET_ACCESS_KEY=%s\n' "$AK" "$SK" > .secrets/s3.env
  chmod 600 .secrets/s3.env
fi
# shellcheck disable=SC1091
source .secrets/s3.env
S3JSON=$(printf '{"identities":[{"name":"admin","credentials":[{"accessKey":"%s","secretKey":"%s"}],"actions":["Admin","Read","Write","List","Tagging"]}]}' "$AWS_ACCESS_KEY_ID" "$AWS_SECRET_ACCESS_KEY")
apply() { kubectl "$@" --dry-run=client -o yaml | kubectl apply -f - >/dev/null; }
apply -n data create secret generic seaweed-s3-config --from-literal=s3.json="$S3JSON"
for ns in pipeline app; do
  apply -n "$ns" create secret generic s3-credentials \
    --from-literal=AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" --from-literal=AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY"
done
echo "secrets created (data/seaweed-s3-config, pipeline+app/s3-credentials)"
