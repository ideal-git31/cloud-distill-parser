"""Check a model output against schema.json. No heavy dependencies, so it is easy to unit-test."""
import json
from pathlib import Path

SCHEMA = json.loads((Path(__file__).with_name("schema.json")).read_text(encoding="utf-8"))
KEYS = set(SCHEMA["keys"])
INTENTS = set(SCHEMA["json_schema"]["properties"]["intent"]["enum"])


def validate_output(raw):
    """Return the parsed dict if `raw` is a valid 4-key command object, else None."""
    try:
        obj = json.loads(raw)
    except (TypeError, ValueError):
        return None
    if not isinstance(obj, dict) or set(obj) != KEYS:
        return None
    if not isinstance(obj["intent"], str) or obj["intent"] not in INTENTS:
        return None
    for k in ("date", "time", "place"):
        if obj[k] is not None and not isinstance(obj[k], str):
            return None
    return obj
