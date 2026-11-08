# Runbook: run everything, in order, and collect the evidence

Save terminal output of the important commands into `results/` (e.g. `... | tee results/task1_cluster.txt`).
Everything below runs on your laptop; only your own measured numbers go into the report.

## 0. One-time setup
```bash
git init && git add -A && git commit -m "initial"        # then create the GitHub repo and push
make up REPO=<owner>/<repo>      # works before any model exists: models are skipped with a message
```

## Task 1: object storage and parallel labelling
```bash
# terminal A (keep running).  NUM_PARALLEL lets the two workers share the teacher.
OLLAMA_HOST=0.0.0.0 OLLAMA_NUM_PARALLEL=2 ollama serve
ollama pull phi3.5

# try the prompt on ~20 commands first (edit prompts/teacher_prompt.txt until the replies are clean JSON)
PYTHONPATH=. .venv/bin/python - <<'PY'
import json
from worker import teacher
t = teacher.load_prompt()
for line in open("data/validation.jsonl").readlines()[:10]:
    print(teacher.ask_teacher(json.loads(line)["text"], t))
PY

make teacher                      # 2 workers in namespace pipeline (indexed Job, SHARD_INDEX 0 and 1)
make teacher-status               # repeat; labelling 3,000 commands on CPU takes hours
kubectl get ns; kubectl -n data get pods; kubectl -n pipeline get pods -o wide | tee results/task1_workers.txt
make clean-data                   # writes datasets/v1/train.jsonl + train.sha256 and results/cleaning_counts.json
make fetch-train                  # verifies the checksum, saves data/v1/train.jsonl
git add data/v1 results/cleaning_counts.json && git commit -m "cleaned dataset"
```
Report: counts from `results/cleaning_counts.json` (input = a + b + c + d + duplicates + kept) and a half-page on sharding.
Run `make clean-data` a second time: the printed sha256 must be identical (it is deterministic).

## Task 2: training (CPU)
```bash
make train SUBSET=50              # smoke test
make train                        # v1 -> training/out/v1, training/loss.csv
make train-v2                     # v2 (one more epoch) -> training/out/v2
make upload-model VERSION=v1      # s3://models/v1/  + copies model.sha256 to models/v1/
make upload-model VERSION=v2
make release VERSION=v1           # GitHub Release asset  model-v1.tar.gz
make release VERSION=v2
git add models training/loss*.csv && git commit -m "model checksums"

make eval-teacher                 # needs Ollama running; writes results/teacher_validation*.json
make eval-base                    # untrained Pythia-70M
make eval-student                 # trained v1
make table                        # side-by-side table for the report
```
Tune `training/config.yaml` (learning rate, epochs) if the student is poor, but report what you actually measured.

## Task 3: container
```bash
docker build -f service/Dockerfile -t cmd-parser:1.0 . && docker images cmd-parser:1.0     # must be <= 2 GB
scripts/mem_test.sh                                                                        # 50 requests at 1 CPU / 1 GiB -> results/memory_test.txt
# FAULT_INJECT check (service must answer 500 {"error":"invalid_model_output"}):
source .secrets/s3.env; scripts/pf.sh start
docker run --rm -p 8002:8000 --add-host=host.docker.internal:host-gateway -e FAULT_INJECT=1 \
  -e MODEL_URI=s3://models/v1/ -e MODEL_VERSION=v1 -e S3_ENDPOINT=http://host.docker.internal:8333 -e MAX_NEW_TOKENS=64 \
  -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY cmd-parser:1.0 &
sleep 30; curl -si -X POST localhost:8002/parse -H 'content-type: application/json' -d '{"text":"hello"}'
```

## Task 4: Kubernetes
```bash
make up && kubectl -n app get deploy,svc,ingress,hpa,pods | tee results/task4_objects.txt
# Service has no endpoints while the model loads: in one terminal run
kubectl -n app get endpoints parser -w
# and in another:  kubectl -n app rollout restart deployment/parser        (endpoints stay empty until /readyz is 200)
# HPA scale up/down: run a long load test and watch
scripts/loadtest.sh hpa 6m & kubectl -n app get hpa -w | tee results/task4_hpa.txt ; kubectl -n app top pods
scripts/rolling_update_test.sh    # v1 -> v2 -> rollout undo, under load
scripts/recovery_test.sh          # delete a Pod under load
kubectl apply -f k8s/30-app.yaml  # restores replicas=2 and the HPA
python scripts/cold_start.py | tee results/cold_start.txt
# load balancing with exactly two Ready replicas (delete the HPA so it cannot scale down):
kubectl -n app delete hpa parser; kubectl -n app scale deployment/parser --replicas=2
kubectl -n app rollout status deployment/parser && make loadtest && cat results/loadtest_headers.json
```
Limitation to state: a single-node k3d cluster on one laptop shows Pod-level recovery only, not tolerance of node or machine
failure; HPA/replicas share the same CPU, so autoscaling gains are limited by the laptop.

## Task 5: network
```bash
python tools/nacl_sim.py network/nacl.json network/packets_sample.jsonl --check
```

## Task 6: CI/CD
```bash
git push -u origin main
python scripts/package_baseline.py && gh release create model-baseline training/out/baseline/model-baseline.tar.gz --title "untrained pythia-70m"
gh workflow run ci.yml -f release_tag=model-baseline     # fails at the quality gate; copy the run URL into the report
git tag final && git push --tags                          # only after everything is committed
```

## Task 7: measurements
```bash
make loadtest                          # results/loadtest_stats.csv, loadtest_headers.json   (while it runs:)
kubectl -n app top pods | tee results/top_pods.txt
python scripts/report_metrics.py --csv results/loadtest_stats.csv --replicas 2 --cpu 1 --mem-gib 1 | tee results/metrics.txt
```
Fill the review table in `report/report.md` using measured values only.
