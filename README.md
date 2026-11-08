# Distilled command parser on a local Kubernetes cloud (CS3081 mini project)

Pipeline: **phi3.5 teacher (Ollama)** labels 3,000 commands in parallel workers -> cleaned dataset in
**SeaweedFS** -> **sequence-level distillation** into **Pythia-70M** (CPU) -> **FastAPI** service in a container ->
**k3d/Kubernetes** (Deployment, Ingress, probes, HPA, rolling update) -> **GitHub Actions** CI with a quality gate.

```
repo
├── cluster/k3d.yaml          k3d cluster (Traefik Ingress on localhost:8080)
├── k8s/                      namespaces, SeaweedFS (data), teacher workers (pipeline), app (app)
├── prompts/teacher_prompt.txt
├── worker/                   worker.py (sharded labelling), clean.py, teacher.py, Dockerfile
├── training/                 config.yaml, train.py, package.py, upload_model.py, loss.csv
├── service/                  FastAPI app, validation, Dockerfile
├── eval/                     teacher/student prediction scripts, results table
├── network/                  subnets.md, nacl.json
├── scripts/                  secrets, port-forward, load/recovery/cold-start/memory tests, cost + SLO
├── tests/  .github/workflows/ci.yml
├── data/ tools/              the student kit (unchanged)
├── models/v1,v2/model.sha256 checksums of the release assets (weights are NOT in Git)
├── results/                  evidence: logs, score reports, Locust output
└── report/report.md  AI_USE.md  docs/RUNBOOK.md
```

## Prerequisites
Docker, k3d, kubectl, make, Python 3.11+, [Ollama](https://ollama.com) with `ollama pull phi3.5`, GitHub CLI (`gh`).
On Windows use WSL2. Set `REPO=<owner>/<repo>` in the Makefile (or `make up REPO=...`) to your GitHub repository.

## Build, deploy, test, tear down
```bash
git clone https://github.com/<owner>/<repo>.git && cd <repo>
make up        # cluster + SeaweedFS + buckets + images + models from the GitHub Release + service
make test      # unit tests          make lint     # ruff
make loadtest  # standard Locust run (needs the service up)
make down      # delete the cluster
```
Then: `curl -s -X POST localhost:8080/parse -H 'content-type: application/json' -d '{"text":"what is the weather in london"}'`

Data and training steps (Tasks 1-2) are separate `make` targets; **docs/RUNBOOK.md** lists every command in order,
including how each piece of evidence for the report is collected.

## Secrets
No credentials are committed. `scripts/make_secrets.sh` generates random S3 keys into `.secrets/` (git-ignored) and
into Kubernetes Secrets. The service and workers read them from the Secret through environment variables.
CI runs gitleaks on every push.
