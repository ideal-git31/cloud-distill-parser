import json

from worker.clean import check_coverage, clean_records, serialise


def rec(i, text, reply):
    return {"id": f"C{i:04d}", "text": text, "teacher_raw": reply if isinstance(reply, str) else json.dumps(reply)}


OK = {"intent": "weather_query", "date": None, "time": None, "place": "london"}


def test_each_rejection_rule_and_duplicates_add_up():
    records = [
        rec(1, "what is the weather in london", OK),                                           # kept
        rec(2, "what is the weather in london", OK),                                           # duplicate of C0001
        rec(3, "set an alarm", "Sure! here you go"),                                           # (a) not JSON
        rec(4, "set an alarm", {"intent": "alarm_set", "date": None}),                         # (b) wrong keys
        rec(5, "set an alarm", {"intent": "play_music", "date": None, "time": None, "place": None}),  # (c) bad intent
        rec(6, "set an alarm for six", {"intent": "alarm_set", "date": None, "time": "6:00", "place": None}),  # (d) not in text
        rec(7, "delete my meeting", {"intent": "calendar_remove", "date": None, "time": None, "place": None}),  # kept
    ]
    kept, counts = clean_records(records)
    assert [r["id"] for r in kept] == ["C0001", "C0007"]
    assert counts == {"input": 7, "a_invalid_json": 1, "b_wrong_keys": 1, "c_bad_intent": 1,
                      "d_bad_slot": 1, "duplicates": 1, "kept": 2}


def test_duplicate_keeps_smallest_id_and_output_is_id_ordered_and_deterministic():
    shuffled = [rec(9, "x in london", OK | {"place": "london"}), rec(2, "x in london", OK), rec(5, "y", {**OK, "place": None})]
    kept, _ = clean_records(shuffled)
    assert [r["id"] for r in kept] == ["C0002", "C0005"]
    assert serialise(kept) == serialise(clean_records(list(reversed(shuffled)))[0])


def test_coverage_detects_gaps_and_repeats():
    gaps, repeats, extra = check_coverage(["C1", "C2", "C3"], ["C1", "C1", "C3", "C9"])
    assert gaps == ["C2"] and repeats == ["C1"] and extra == ["C9"]
