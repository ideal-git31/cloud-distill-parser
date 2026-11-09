# `>` at the start of a line is converted to a TAB when the Makefile is generated.
SHELL := /bin/bash
REPO     ?= ideal-git31/cloud-distill-parser
CLUSTER  := cloudlab
PYTHON3  ?= python3
PY       := .venv/bin/python
S3ENV := . .secrets/s3.env && export S3_ENDPOINT=http://localhost:8333 PYTHONPATH=.
CONFIG   ?= training/config.yaml
VERSION  ?= v1

.PHONY: up down venv cluster secrets storage buckets images seed-models deploy \
        teacher teacher-status clean-data fetch-train train train-v2 upload-model release \
        eval-teacher eval-base eval-student table loadtest metrics test lint

## ---- whole system: fresh clone ->  git clone ...; cd ...; make up -------------------------------
up: venv cluster secrets storage buckets images seed-models deploy
	@echo "System is up. Try: curl -s -X POST localhost:8080/parse -H 'content-type: application/json' -d '{\"text\":\"what is the weather in london\"}'"

down:
	-scripts/pf.sh stop
	-k3d cluster delete $(CLUSTER)

venv: .venv/.ok
.venv/.ok: requirements-dev.txt
	$(PYTHON3) -m venv .venv
	.venv/bin/pip install -q -r requirements-dev.txt
	touch $@

.venv/.train-ok: .venv/.ok training/requirements.txt
	.venv/bin/pip install -q -r training/requirements.txt
	touch $@

cluster:
	k3d cluster list $(CLUSTER) >/dev/null 2>&1 || k3d cluster create --config cluster/k3d.yaml
	kubectl apply -f k8s/00-namespaces.yaml

secrets:
	scripts/make_secrets.sh

storage:
	kubectl apply -f k8s/10-seaweedfs.yaml
	kubectl -n data rollout status deployment/seaweedfs --timeout=300s

buckets: venv
	scripts/pf.sh start
	$(S3ENV) && $(PY) scripts/bootstrap_storage.py

images:
	docker build -f service/Dockerfile -t cmd-parser:1.0 .
	docker build -f worker/Dockerfile -t labeler-worker:1.0 .
	k3d image import cmd-parser:1.0 labeler-worker:1.0 -c $(CLUSTER)

seed-models: venv
	scripts/pf.sh start
	$(S3ENV) && PYTHON=$(PY) scripts/seed_models.sh $(REPO)

deploy:
	kubectl apply -f k8s/30-app.yaml
	@if [ -f models/v1/model.sha256 ]; then \
		kubectl -n app rollout status deployment/parser --timeout=600s; \
	else \
		echo "No trained v1 model yet; application Pods are expected to remain unready."; \
	fi

## ---- Task 1: teacher labelling ---------------------------------------------------------------------
# Start Ollama first:  OLLAMA_HOST=0.0.0.0 ollama serve   and   ollama pull phi3.5
teacher:
	kubectl apply -f k8s/20-teacher-workers.yaml
teacher-status:
	kubectl -n pipeline get jobs,pods
	kubectl -n pipeline logs -l job-name=teacher-labeller --tail=3 --prefix
clean-data: venv
	scripts/pf.sh start
	$(S3ENV) && $(PY) -m worker.clean
fetch-train: venv
	scripts/pf.sh start
	$(S3ENV) && $(PY) scripts/fetch_train.py

## ---- Task 2: training (CPU) -------------------------------------------------------------------------
data/v1/train.jsonl:
	$(MAKE) fetch-train
# make train                 -> trains v1 from training/config.yaml
# make train SUBSET=50       -> smoke test on the first 50 records
train: .venv/.train-ok data/v1/train.jsonl
	$(PY) training/train.py --config $(CONFIG) $(if $(SUBSET),--subset $(SUBSET),)
train-v2:
	$(MAKE) train CONFIG=training/config_v2.yaml
upload-model: venv
	scripts/pf.sh start
	$(S3ENV) && $(PY) training/upload_model.py --dir training/out/$(VERSION) --version $(VERSION)
	mkdir -p models/$(VERSION) && cp training/out/$(VERSION)/model.sha256 models/$(VERSION)/model.sha256
release:
	gh release create model-$(VERSION) training/out/$(VERSION)/model-$(VERSION).tar.gz --title "model $(VERSION)" --notes "Pythia-70M distilled from phi3.5. sha256 in models/$(VERSION)/model.sha256"

eval-teacher:
	$(PY) eval/predict_teacher.py --out results/teacher_validation_predictions.jsonl
	$(PY) tools/score.py results/teacher_validation_predictions.jsonl data/validation.jsonl --out results/teacher_validation.json
eval-base: .venv/.train-ok
	$(PY) eval/predict_student.py --model EleutherAI/pythia-70m --out results/base_validation_predictions.jsonl
	$(PY) tools/score.py results/base_validation_predictions.jsonl data/validation.jsonl --out results/base_validation.json
eval-student: .venv/.train-ok
	$(PY) eval/predict_student.py --model training/out/v1 --out results/student_v1_validation_predictions.jsonl
	$(PY) tools/score.py results/student_v1_validation_predictions.jsonl data/validation.jsonl --out results/student_v1_validation.json
table:
	$(PY) eval/make_table.py

## ---- Task 7 / quality ---------------------------------------------------------------------------------
loadtest: venv
	PATH=$$PWD/.venv/bin:$$PATH scripts/loadtest.sh loadtest 2m
metrics:
	$(PY) scripts/report_metrics.py --csv results/loadtest_stats.csv --replicas 2 --cpu 1 --mem-gib 1
test: venv
	$(PY) -m pytest -q
lint: venv
	.venv/bin/ruff check .
