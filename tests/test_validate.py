import json

import pytest

from service.validate import validate_output

GOOD = {"intent": "weather_query", "date": None, "time": None, "place": "london"}


def test_accepts_valid_object():
    assert validate_output(json.dumps(GOOD)) == GOOD


@pytest.mark.parametrize("raw", [
    "not json",
    '{"intent": "alarm_set", "date": "tomor',                                  # truncated output
    '[1, 2]',                                                                    # not an object
    '{"intent": "alarm_set", "date": null, "time": null}',                      # missing key
    '{"intent": "alarm_set", "date": null, "time": null, "place": null, "x": 1}',  # extra key
    '{"intent": "make_coffee", "date": null, "time": null, "place": null}',     # unknown intent
    '{"intent": "alarm_set", "date": 5, "time": null, "place": null}',          # slot is not text
    None,
])
def test_rejects_invalid_output(raw):
    assert validate_output(raw) is None
