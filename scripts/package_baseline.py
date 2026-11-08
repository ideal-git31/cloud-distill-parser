"""Package the UNTRAINED Pythia-70M as a release asset (the deliberately bad model for the CI quality-gate demo).

    python scripts/package_baseline.py            -> training/out/baseline/model-baseline.tar.gz
    gh release create model-baseline training/out/baseline/model-baseline.tar.gz --title "untrained pythia-70m"
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from transformers import AutoModelForCausalLM, AutoTokenizer  # noqa: E402

from training.package import package  # noqa: E402

out = Path("training/out/baseline")
out.mkdir(parents=True, exist_ok=True)
AutoModelForCausalLM.from_pretrained("EleutherAI/pythia-70m").save_pretrained(out, safe_serialization=True)
AutoTokenizer.from_pretrained("EleutherAI/pythia-70m").save_pretrained(out)
print(package(out, "baseline"))
