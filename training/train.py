"""Sequence-level knowledge distillation: fine-tune Pythia-70M on the teacher's JSON replies (CPU).

    python training/train.py --config training/config.yaml [--subset N]

Training example:   Command: <command>\nJSON: <teacher's JSON reply><eos>
Only the JSON part (and eos) contributes to the loss; the prompt tokens are masked with -100.
"""
import argparse
import csv
import hashlib
import json
import platform
import random
import sys
import time
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.prompt import build_prompt, build_target  # noqa: E402


def load_examples(path, limit):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
            if len(rows) >= limit:
                break
    return rows


def encode_example(tok, row, max_len):
    obj = json.loads(row["teacher_raw"].strip())  # teacher reply, parsed only to give it one canonical layout
    prompt_ids = tok(build_prompt(row["text"]))["input_ids"]
    target_ids = tok(build_target(obj))["input_ids"] + [tok.eos_token_id]
    ids = (prompt_ids + target_ids)[:max_len]
    labels = ([-100] * len(prompt_ids) + target_ids)[:max_len]
    return ids, labels


def collate(batch, pad_id):
    import torch
    n = max(len(ids) for ids, _ in batch)
    input_ids = torch.full((len(batch), n), pad_id, dtype=torch.long)
    labels = torch.full((len(batch), n), -100, dtype=torch.long)
    attn = torch.zeros((len(batch), n), dtype=torch.long)
    for i, (ids, lab) in enumerate(batch):
        input_ids[i, : len(ids)] = torch.tensor(ids)
        labels[i, : len(lab)] = torch.tensor(lab)
        attn[i, : len(ids)] = 1
    return {"input_ids": input_ids, "attention_mask": attn, "labels": labels}


def run_training(model, tok, examples, cfg):
    """Plain PyTorch loop. Returns the mean training loss of every epoch."""
    import torch
    from transformers import get_linear_schedule_with_warmup

    torch.manual_seed(cfg["seed"])
    gen = torch.Generator().manual_seed(cfg["seed"])
    loader = torch.utils.data.DataLoader(
        examples, batch_size=cfg["batch_size"], shuffle=True, generator=gen,
        collate_fn=lambda b: collate(b, tok.pad_token_id),
    )
    opt = torch.optim.AdamW(model.parameters(), lr=cfg["learning_rate"], weight_decay=cfg["weight_decay"])
    total = cfg["epochs"] * len(loader)
    sched = get_linear_schedule_with_warmup(opt, int(cfg["warmup_ratio"] * total), total)
    model.train()
    losses = []
    for epoch in range(1, cfg["epochs"] + 1):
        t0, running, steps = time.time(), 0.0, 0
        for batch in loader:
            out = model(**batch)
            out.loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            sched.step()
            opt.zero_grad()
            running += out.loss.item()
            steps += 1
        losses.append(running / steps)
        print(f"epoch {epoch}/{cfg['epochs']}  loss {losses[-1]:.4f}  ({time.time() - t0:.0f}s)", flush=True)
    return losses


def library_versions():
    import numpy
    import torch
    import transformers
    return {"python": platform.python_version(), "torch": torch.__version__,
            "transformers": transformers.__version__, "numpy": numpy.__version__, "pyyaml": yaml.__version__}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="training/config.yaml")
    ap.add_argument("--subset", type=int, default=None, help="train on the first N records only (smoke test)")
    a = ap.parse_args()
    cfg = yaml.safe_load(open(a.config))

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, set_seed

    random.seed(cfg["seed"])
    set_seed(cfg["seed"])

    limit = min(cfg["max_examples"], a.subset) if a.subset else cfg["max_examples"]
    rows = load_examples(cfg["train_file"], limit)
    print(f"training on {len(rows)} examples (limit {limit}) from {cfg['train_file']}")

    tok = AutoTokenizer.from_pretrained(cfg["base_model"])
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(cfg["base_model"], torch_dtype=torch.float32)
    examples = [encode_example(tok, r, cfg["max_seq_length"]) for r in rows]

    losses = run_training(model, tok, examples, cfg)

    loss_csv = Path(cfg["loss_csv"] if not a.subset else cfg["loss_csv"].replace(".csv", "_subset.csv"))
    loss_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(loss_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["epoch", "loss"])
        for i, v in enumerate(losses, 1):
            w.writerow([i, f"{v:.6f}"])

    version = cfg["output_version"] + ("-subset" if a.subset else "")
    out_dir = Path(cfg["output_root"]) / version
    out_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(out_dir, safe_serialization=True)
    tok.save_pretrained(out_dir)
    info = {
        "model_version": version, "base_model": cfg["base_model"], "examples": len(rows),
        "train_file_sha256": hashlib.sha256(Path(cfg["train_file"]).read_bytes()).hexdigest(),
        "config": {k: v for k, v in cfg.items() if k != "library_versions"},
        "library_versions": library_versions(), "epoch_loss": losses,
    }
    (out_dir / "version.json").write_text(json.dumps(info, indent=2) + "\n")

    from training.package import package
    archive, digest = package(out_dir, version)
    print(f"saved {out_dir}\narchive {archive.name}\nsha256 {digest}")


if __name__ == "__main__":
    main()
