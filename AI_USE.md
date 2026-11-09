# AI Use Declaration

## Tools used

- **Claude (Anthropic):** Assisted in generating the initial repository skeleton and first drafts of the Makefile, Kubernetes manifests, worker, cleaning script, training script, inference service, tests, CI workflow and documentation.
- **ChatGPT (OpenAI):** Assisted with iterative debugging, implementation changes, Kubernetes and Docker troubleshooting, interpreting test results, and preparing technical documentation.
- **Ollama with Phi-3.5 Mini Instruct:** Used as the teacher model to generate command-to-JSON labels. Teacher responses were produced by the model, not written by ChatGPT.

## What AI did not do

- ChatGPT did not generate the teacher-label dataset.
- The reported measurements were collected by running commands and tests in the project environment.
- The validation set was used for evaluation, not training.
- The handwritten reflection must be written by the student.

## Verification performed

- Executed the project unit tests: 21 passed, 1 skipped.
- Executed Ruff linting successfully.
- Ran the teacher-label cleaning and coverage checks.
- Trained and evaluated both student model versions.
- Tested Docker inference, Kubernetes deployment, health/readiness probes, autoscaling and Pod recovery.
- Ran the NACL packet simulator: 6 of 6 sample cases passed.
- Ran a 50-request memory test and a 63-request load test.
- Verified the GitHub Actions pipeline, including lint, unit tests, secret scanning, model evaluation and the JSON-validity quality gate.

## Limitations and corrections

- The intended dataset size was 3,000 commands, but only 600 commands were labelled during this experiment. Cleaning retained 513 examples.
- The student models were trained on 513 examples rather than the intended 1,500.
- The initial CI workflow used a nonexistent model-v1 release as its push-event fallback. This was corrected to model-v2.
- The memory test was updated to use model-v2 because model-v1 was not uploaded to SeaweedFS.
- The local Kubernetes cluster demonstrates deployment and Pod-level recovery, not multi-node cloud fault tolerance.

The student should review this declaration and ensure it accurately represents their own contribution before submission.
