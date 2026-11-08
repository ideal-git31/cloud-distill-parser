"""Training / inference prompt format shared by training, evaluation and the service."""
import json

KEYS = ("intent", "date", "time", "place")


def build_prompt(text):
    return f"Command: {text}\nJSON:"


def build_target(obj):
    """Canonical text of the teacher's reply (key order fixed, one line)."""
    return " " + json.dumps({k: obj[k] for k in KEYS})
