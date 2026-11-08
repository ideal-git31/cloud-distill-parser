"""Training-loop smoke test with a tiny random GPT-NeoX and a character tokenizer (no downloads).
Skipped automatically when PyTorch / Transformers are not installed (e.g. in the light CI test job)."""
import json

import pytest

torch = pytest.importorskip("torch")
transformers = pytest.importorskip("transformers")

from training.package import package, sha256_file  # noqa: E402
from training.train import encode_example, run_training  # noqa: E402


class CharTok:
    eos_token_id = 0
    pad_token_id = 0

    def __call__(self, text):
        return {"input_ids": [min(ord(c), 120) + 1 for c in text]}


def tiny_model():
    cfg = transformers.GPTNeoXConfig(vocab_size=130, hidden_size=32, num_hidden_layers=2,
                                     num_attention_heads=2, intermediate_size=64, max_position_embeddings=256)
    return transformers.GPTNeoXForCausalLM(cfg)


ROWS = [{"id": f"C{i}", "text": f"set an alarm for {i} am",
         "teacher_raw": json.dumps({"intent": "alarm_set", "date": None, "time": f"{i} am", "place": None})} for i in range(1, 9)]


def test_prompt_tokens_are_masked_and_target_ends_with_eos():
    ids, labels = encode_example(CharTok(), ROWS[0], 256)
    assert len(ids) == len(labels) and labels[-1] == 0
    n_masked = sum(1 for x in labels if x == -100)
    assert 0 < n_masked < len(labels)


def test_loss_goes_down_and_is_reproducible():
    cfg = {"seed": 42, "learning_rate": 5e-3, "batch_size": 4, "epochs": 6, "weight_decay": 0.0, "warmup_ratio": 0.0}
    ex = [encode_example(CharTok(), r, 256) for r in ROWS]
    torch.manual_seed(0)
    a = run_training(tiny_model(), CharTok(), ex, cfg)
    torch.manual_seed(0)
    b = run_training(tiny_model(), CharTok(), ex, cfg)
    assert a[-1] < a[0]
    assert a == pytest.approx(b)


def test_package_is_deterministic(tmp_path):
    (tmp_path / "model.safetensors").write_bytes(b"weights")
    (tmp_path / "config.json").write_text("{}")
    _, h1 = package(tmp_path, "t")
    _, h2 = package(tmp_path, "t")
    assert h1 == h2 and (tmp_path / "model.sha256").read_text().split()[0] == sha256_file(tmp_path / "model-t.tar.gz")
