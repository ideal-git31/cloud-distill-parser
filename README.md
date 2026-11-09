# Distilled Command Parser on a Local Kubernetes Cloud

**CS3081 Cloud Computing Mini Project**

A lightweight natural-language command parser built through sequence-level knowledge distillation. The project uses Phi-3.5 Mini as the teacher, EleutherAI Pythia-70M as the student, SeaweedFS for S3-compatible object storage, FastAPI for inference, and k3d/Kubernetes for deployment.

**Repository:** https://github.com/ideal-git31/cloud-distill-parser
**Model release:** https://github.com/ideal-git31/cloud-distill-parser/releases/tag/model-v2

## 1. Architecture

```text
Command Pool (JSONL)
       |
       v
SeaweedFS Object Storage
       |
       v
Two Parallel Teacher Workers
(Phi-3.5 Mini through Ollama)
       |
       v
Raw Teacher Outputs
       |
       v
Cleaning and Validation
       |
       v
Cleaned Training Dataset
       |
       v
Pythia-70M Sequence-Level Distillation
(CPU; v1 and v2)
       |
       v
SeaweedFS + GitHub Release
       |
       v
FastAPI Docker Inference Service
       |
       v
Kubernetes Deployment
(HPA, probes, rolling updates)
       |
       v
Client /parse API
```

## 2. Implementation and Dataset

The teacher is Phi-3.5 Mini Instruct served through Ollama. Two Kubernetes worker pods process separate shards using line-number modulo partitioning.

The assignment target was 3,000 unlabelled commands. Due to execution-time and local-resource constraints, this implementation processed **600 commands**:

| Dataset stage | Count |
|---|---:|
| Commands teacher-labelled | 600 |
| Valid JSON teacher responses | 522 |
| Invalid JSON responses | 78 |
| Additional bad-slot records rejected | 9 |
| Final cleaned training examples | 513 |

The cleaning stage checks JSON validity, exact keys, allowed intents, slot values against the original command, and duplicate records. The validation dataset is kept separate from training.

Cleaned dataset:
- `data/v1/train.jsonl`
- `data/v1/train.sha256`

SHA-256:
`620dea5d8951ec84c8ec925e7f838e71807b35ca5fa1fb6d5fe83e41c089ee2`

## 3. Student Model and Evaluation

The student model is `EleutherAI/pythia-70m`, fine-tuned using sequence-level distillation on CPU. The prompt portion is masked from the training loss; the teacher-generated JSON response is the target.

Two model versions were trained. The 100-example validation set was used only for evaluation.

| Metric | Base Pythia-70M | Student v1 | Student v2 |
|---|---:|---:|---:|
| JSON validity | 0% | 98% | 100% |
| Intent accuracy | 0% | 80% | 83% |
| Date accuracy | 0% | 76% | 75% |
| Time accuracy | 0% | 85% | 86% |
| Place accuracy | 0% | 81% | 82% |
| Full-frame accuracy | 0% | 45% | 44% |

**Deployment choice: v2.** It achieved 100% JSON validity and the best intent, time, and place accuracy. v1 scored slightly better on date and full-frame accuracy. Full-frame accuracy remains a limitation.

Model weights are stored outside Git, in SeaweedFS and the GitHub Release:
- [model-v2 release](https://github.com/ideal-git31/cloud-distill-parser/releases/tag/model-v2)
- Model archive SHA-256: `a948ff57c646363a5020fbfc751d4929feff17dfae814db1cd24a37ee7ca7fbf`

## 4. Inference API

The FastAPI service exposes:

| Endpoint | Purpose |
|---|---|
| `GET /healthz` | Process liveness |
| `GET /readyz` | Model readiness |
| `POST /parse` | Parse a natural-language command |

The parse response follows the exact schema:

```json
{
  "intent": "weather_query",
  "date": null,
  "time": null,
  "place": "london"
}
```

Responses include:
- `X-Model-Version`
- `X-Served-By`

The model is downloaded from S3-compatible object storage during service startup.

## 5. Kubernetes and Reliability

The local cluster is created with k3d. The deployment includes:
- Kubernetes Deployment and Service
- Ingress for `/parse`
- Liveness and readiness probes
- Rolling update configuration
- Horizontal Pod Autoscaler: 1–2 replicas, 70% CPU target
- SeaweedFS object storage
- Kubernetes Secrets for storage credentials

Observed tests:
- HPA scaled from one to two replicas under load and returned to one.
- Both replicas served load-test requests.
- Deleted application pods were recreated and became Ready.
- Three cold-start trials each took approximately 5 seconds from pod creation to readiness.

## 6. Networking

The networking exercise uses VLSM subnet allocation from `10.20.0.0/16`:

| Subnet | CIDR | Usable hosts |
|---|---|---:|
| App | `10.20.0.0/22` | 1022 |
| Public | `10.20.4.0/24` | 254 |
| Data | `10.20.5.0/25` | 126 |
| Management | `10.20.5.128/27` | 30 |

A stateless NACL simulator checks inbound and outbound rules, including ephemeral return traffic. All six supplied packet scenarios passed. This is a simulator, not a deployed AWS VPC NACL.

## 7. Performance and Cost

Measured Locust load-test summary:

| Metric | Result |
|---|---:|
| Requests | 63 |
| Failures | 0 |
| Error rate | 0% |
| Median latency | 4,800 ms |
| p95 latency | 16,000 ms |
| Throughput | 0.546 requests/s |

Memory test:
- 50/50 requests returned HTTP 200.
- Peak container memory was approximately 1005.5 MiB against a 1 GiB limit.
- OOMKilled: false.

Estimated cost using the supplied rate card:
- Two replicas: INR 7.90/hour.
- Estimated cost per 1,000 requests: approximately INR 4.02.

These are local test measurements and rate-card estimates, not actual cloud-provider billing. The memory result also indicates limited headroom under the tested configuration.

## 8. Repository Structure

```text
.github/workflows/   CI workflow
cluster/             k3d cluster configuration
common/              Shared utilities and S3 support
data/                Command pool, schema, validation data
docs/                Runbook and supporting documentation
eval/                Evaluation scripts
k8s/                 Kubernetes manifests
models/              Model checksums (not model weights)
network/              Subnet and NACL exercises
prompts/              Teacher prompt
report/               Project report (Markdown and PDF)
scripts/              Setup, load, recovery and memory scripts
service/              FastAPI inference service and Dockerfile
tests/                Unit tests
tools/                Evaluation and NACL tools
training/             Training scripts and loss records
worker/               Teacher labelling and cleaning workers
AI_USE.md              AI assistance disclosure
```

## 9. Prerequisites

- macOS/Linux or Windows with WSL2
- Docker
- k3d
- kubectl
- GNU Make
- Python 3.11
- Ollama with `phi3.5` available for teacher labelling
- Git and GitHub CLI (`gh`) for release operations

## 10. Setup and Commands

Clone the repository:

```bash
git clone https://github.com/ideal-git31/cloud-distill-parser.git
cd cloud-distill-parser
```

Create and activate the Python environment:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

Run local quality checks:

```bash
make test PYTHON3=python3.11
make lint
```

Start the local cluster and project infrastructure:

```bash
make up
```

Send an inference request after deployment:

```bash
curl -s -X POST http://localhost:8080/parse \
  -H 'Content-Type: application/json' \
  -d '{"text":"what is the weather in london"}'
```

Run the load test:

```bash
make loadtest PYTHON3=python3.11
```

Tear down the local cluster:

```bash
make down
```

For the complete task-by-task workflow, use `docs/RUNBOOK.md`. Teacher labelling requires Ollama running and reachable by the Kubernetes workers. Training and model-release operations are documented in the runbook and Makefile.

## 11. CI/CD and Reproducibility

GitHub Actions runs linting, unit tests, secret scanning, model evaluation, and a JSON-validity quality gate. The quality gate requires at least 95% valid JSON.

The latest verified workflow run passed all five jobs:

https://github.com/ideal-git31/cloud-distill-parser/actions/runs/42536834551

Reproducibility evidence is retained in `results/`, including cleaning counts, validation scores, load-test summaries, and memory-test output.

## 12. Limitations

- 600 commands were processed instead of the 3,000-command target.
- 513 cleaned examples were available for training, rather than the intended 1,500.
- Full-frame validation accuracy is 44% for v2.
- The local single-node k3d environment does not represent a production multi-node cloud.
- The memory test reached approximately 98% of the configured 1 GiB limit.
- Cost values are estimates based on the supplied rate card.

## 13. Documentation

- `docs/RUNBOOK.md` — operational instructions
- `report/report.md` — report source
- `report/report.pdf` — final project report
- `AI_USE.md` — AI usage disclosure

## Acknowledgements

The project uses Phi-3.5 Mini Instruct, EleutherAI Pythia-70M, Ollama, SeaweedFS, FastAPI, Docker, Kubernetes, k3d, and GitHub Actions.
