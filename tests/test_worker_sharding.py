import json

import pytest

from worker.teacher import render
from worker.worker import select_shard

LINES = [json.dumps({"id": f"C{i:04d}", "text": f"cmd {i}"}) for i in range(10)]


def test_shards_partition_the_pool_without_gaps_or_repeats():
    shards = [[r["id"] for r in select_shard(LINES, i, 3)] for i in range(3)]
    flat = sorted(x for s in shards for x in s)
    assert flat == [f"C{i:04d}" for i in range(10)]
    assert shards[1] == ["C0001", "C0004", "C0007"]          # line numbers with remainder 1 (counting from 0)


def test_invalid_shard_index_is_rejected():
    with pytest.raises(ValueError):
        list(select_shard(LINES, 3, 3))


def test_prompt_rendering_keeps_json_braces_and_inserts_command():
    out = render('JSON: {"intent": "x"}\nCommand: {command}\nJSON:', "hello world")
    assert '{"intent": "x"}' in out and "Command: hello world" in out
