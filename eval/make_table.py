"""Print the three score reports side by side as a Markdown table (for the report)."""
import json
from pathlib import Path

FILES = [("Teacher (phi3.5)", "results/teacher_validation.json"),
         ("Pythia-70M untrained", "results/base_validation.json"),
         ("Student v1 (distilled)", "results/student_v1_validation.json")]
METRICS = ["json_validity", "intent_accuracy", "date_accuracy", "time_accuracy", "place_accuracy", "full_frame"]

reports = [(n, json.loads(Path(p).read_text())) for n, p in FILES if Path(p).exists()]
print("| metric (%) | " + " | ".join(n for n, _ in reports) + " |")
print("|---|" + "---|" * len(reports))
for m in METRICS:
    print(f"| {m} | " + " | ".join(str(r[m]) for _, r in reports) + " |")
