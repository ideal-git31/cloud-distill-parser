---
title: "Distillation and deployment of a command-parsing LM on a local cloud"
author: "<name>, <roll number>"
---

> Template. Keep measured results and assumptions clearly separate. Replace every TODO with your own numbers.
> Convert with: `pandoc report/report.md -o report/report.pdf`  (max 8 pages without references/appendices).

## 1. Architecture and decisions
<diagram: laptop (Ollama) -> pipeline workers -> SeaweedFS (datasets, models) -> training -> models/v1,v2 -> service Pods -> Traefik Ingress>
TODO: why k3d, why an Indexed Job, why S3 for weights, why CPU-only PyTorch.

## 2. Task 1: storage and parallel labelling
**Sharding (assumption-free description).** `cmd` line number `n` (from 0) goes to shard `n mod SHARD_COUNT`; with 2 workers,
worker 0 takes even lines and worker 1 odd lines. The sets are disjoint and together cover the pool, so every id appears
in exactly one shard. Each worker checkpoints its object every 25 records, so a restarted Pod resumes instead of restarting.
`clean.py` verifies coverage (no gaps, no repeats) before cleaning.

Measured counts (from `results/cleaning_counts.json`):

| input | (a) not JSON | (b) wrong keys | (c) bad intent | (d) bad slot | duplicates | kept |
|---|---|---|---|---|---|---|
| TODO | TODO | TODO | TODO | TODO | TODO | TODO |

Order of checks: (a), (b), (c), (d) per record, then duplicates among the records that passed (smallest id kept).
SHA-256 of `train.jsonl`: TODO.

## 3. Task 2: sequence-level distillation
Config (`training/config.yaml`): seed, learning rate, batch size, epochs, max length, library versions. Loss per epoch: TODO (`training/loss.csv`).

| metric (%) | Teacher phi3.5 | Pythia-70M untrained | Student v1 |
|---|---|---|---|
| json_validity | TODO | TODO | TODO |
| intent_accuracy | TODO | TODO | TODO |
| date_accuracy | TODO | TODO | TODO |
| time_accuracy | TODO | TODO | TODO |
| place_accuracy | TODO | TODO | TODO |
| full_frame | TODO | TODO | TODO |

What changed and why: TODO. Suitability of Pythia-70M: TODO (tiny English-only base model, 2,048-token context, no instruction
tuning; adequate only because the task is narrow and the output format is fixed).

**Sequence-level vs logit-based distillation (draft, rewrite in your own words).**
Sequence-level KD (Kim and Rush, 2016) trains the student with ordinary cross-entropy on the *text* the teacher generated
(Command -> teacher JSON). Logit-based KD trains the student to match the teacher's *probability distribution over the next
token* at each position (e.g. KL divergence on logits), which carries much more information per example. It is not possible
here because the teacher and student use different tokenizers/vocabularies (phi3.5 vs the GPT-NeoX tokenizer of Pythia),
so their output distributions are not aligned, and the labelling was done through Ollama, which returns text, not logits.
Limitation (TODO choose a real one you can support): the student only copies the teacher's mistakes, 1,500 examples is small,
and the validation set (100 commands) gives wide error bars.

## 4. Task 3: container
Image size TODO MB (`docker images`). Peak memory over 50 sequential requests at 1 CPU / 1 GiB: TODO (`results/memory_test.txt`).

## 5. Task 4: Kubernetes
Resources requests/limits, probes, HPA (min 1, max 2, 70% CPU): TODO evidence. Rolling update failure rate: TODO. Recovery: TODO.
Cold start (3 runs): TODO, TODO, TODO, median TODO. Load balancing per replica: TODO / TODO.
**Limitation:** single-node cluster on one laptop. It shows Pod recovery, not node or multi-machine fault tolerance.

## 6. Task 5: network
See `network/subnets.md` (table, working, NACL, explanations).

## 7. Task 6: CI/CD
Link to the run that failed at the quality gate: TODO. Secret scan result: TODO.

## 8. Task 7: performance, cost and review
p50 TODO ms, p95 TODO ms, throughput TODO req/s, error rate TODO %. `kubectl top pods`: TODO. Cold start: TODO.
Cost per 1,000 requests: hourly = replicas x (CPU limit x 3.50 + memory limit GiB x 0.45) = TODO; requests/hour = rps x 3600 = TODO; result TODO INR.
SLO: 99% of requests succeed during one load-test run; error budget TODO requests; used TODO.

| Component | Evidence (measured) | Limitation | Improvement |
|---|---|---|---|
| Data and storage | TODO | TODO | TODO |
| Model quality | TODO | TODO | TODO |
| Latency and throughput | TODO | TODO | TODO |
| Resource utilisation | TODO | TODO | TODO |
| Reliability and recovery | TODO | TODO | TODO |
| Security and cost | TODO | TODO | TODO |
