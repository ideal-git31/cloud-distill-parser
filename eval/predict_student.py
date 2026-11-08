"""Run a causal LM (trained student, or the untrained base model) on a labelled file and write raw predictions.

    python eval/predict_student.py --model training/out/v1 --data data/validation.jsonl \
        --out results/student_v1_validation_predictions.jsonl
    python eval/predict_student.py --model EleutherAI/pythia-70m ...        # untrained baseline
Output lines: {"id": "V001", "prediction": "<raw generated text>"} for tools/score.py
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.prompt import build_prompt  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--data", default="data/validation.jsonl")
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-new-tokens", type=int, default=64)
    a = ap.parse_args()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(a.model)
    model = AutoModelForCausalLM.from_pretrained(a.model, torch_dtype=torch.float32).eval()
    rows = [json.loads(x) for x in open(a.data, encoding="utf-8") if x.strip()]
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        for i, r in enumerate(rows, 1):
            enc = tok(build_prompt(r["text"]), return_tensors="pt")
            with torch.inference_mode():
                out = model.generate(**enc, max_new_tokens=a.max_new_tokens, do_sample=False, pad_token_id=tok.eos_token_id)
            text = tok.decode(out[0][enc["input_ids"].shape[1]:], skip_special_tokens=True).strip().split("\n")[0].strip()
            f.write(json.dumps({"id": r["id"], "prediction": text}) + "\n")
            if i % 20 == 0:
                print(f"{i}/{len(rows)}", flush=True)
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
