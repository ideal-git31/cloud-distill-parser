"""Call the teacher (phi3.5 on Ollama) with temperature 0 and seed 42."""
import os
import time
from pathlib import Path

import requests

MODEL = "phi3.5"
PROMPT_PATH = Path(os.environ.get("TEACHER_PROMPT", Path(__file__).resolve().parent.parent / "prompts" / "teacher_prompt.txt"))


def load_prompt(path=PROMPT_PATH):
    return Path(path).read_text(encoding="utf-8")


def render(template, command):
    # str.replace (not str.format): the prompt itself contains JSON braces
    return template.replace("{command}", command)


def ask_teacher(command, template, url=None, retries=5):
    url = (url or os.environ.get("OLLAMA_URL", "http://localhost:11434")).rstrip("/")
    body = {
        "model": MODEL,
        "prompt": render(template, command),
        "stream": False,
        "options": {"temperature": 0, "seed": 42, "num_predict": 120},
    }
    last = None
    for attempt in range(retries):
        try:
            r = requests.post(f"{url}/api/generate", json=body, timeout=600)
            r.raise_for_status()
            return r.json()["response"]  # stored exactly as generated
        except Exception as exc:  # network hiccup / Ollama busy: back off and retry
            last = exc
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"teacher failed for {command!r}: {last}")
