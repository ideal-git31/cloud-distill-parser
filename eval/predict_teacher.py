"""Run the teacher (same prompt and settings as Task 1) on validation.jsonl and write raw predictions."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from worker import teacher  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/validation.jsonl")
    ap.add_argument("--out", default="results/teacher_validation_predictions.jsonl")
    ap.add_argument("--url", default=None, help="Ollama URL (default $OLLAMA_URL or http://localhost:11434)")
    a = ap.parse_args()
    template = teacher.load_prompt()
    rows = [json.loads(x) for x in open(a.data, encoding="utf-8") if x.strip()]
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        for i, r in enumerate(rows, 1):
            raw = teacher.ask_teacher(r["text"], template, url=a.url)
            f.write(json.dumps({"id": r["id"], "prediction": raw}, ensure_ascii=False) + "\n")
            if i % 10 == 0:
                print(f"{i}/{len(rows)}", flush=True)
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
