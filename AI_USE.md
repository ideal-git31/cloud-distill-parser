# AI use

> DRAFT: edit this so it is true for YOU. Replace every <...> with what you actually did.

## Tools used
- Claude (Anthropic, claude.ai): generated the first version of the repository skeleton (Makefile, Kubernetes manifests,
  worker, cleaning script, training script, service, tests, CI workflow, documentation drafts).
- <any other tool, e.g. GitHub Copilot, ChatGPT: what for>

## What AI did NOT do
- The teacher labels were produced by phi3.5 through Ollama and were never edited by hand.
- All numbers in the report (counts, scores, latency, memory, cost) come from commands I ran myself.
- <the handwritten reflection was written by me>

## How I checked the AI's output
- Read every file and ran it: <which parts you read line by line>
- Unit tests (`make test`) and lint (`make lint`); <what you added or fixed>
- Verified against the assignment text: <e.g. checked the cleaning rules (a)-(e), NACL rule order, shard formula>
- Things the AI got wrong or I had to fix: <be specific, e.g. image build error, manifest field, prompt rewrite>
- Concepts I looked up myself: <KD papers, Kubernetes probes, NACL statelessness, ...>
