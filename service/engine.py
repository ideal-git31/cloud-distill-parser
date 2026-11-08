"""Model loading (from object storage) and generation."""
import logging
import os
import time

from common import s3util
from common.prompt import build_prompt

log = logging.getLogger("engine")
MODEL_DIR = "/tmp/model"


class Engine:
    def __init__(self):
        self._ready = False
        self.model = None
        self.tok = None

    @property
    def ready(self):
        return self._ready

    def load(self):
        """Download the model + tokenizer from MODEL_URI (S3_ENDPOINT) and load them. Retries until storage is up."""
        uri = os.environ["MODEL_URI"]
        bucket, prefix = s3util.parse_uri(uri)
        for attempt in range(1, 61):
            try:
                log.warning("downloading model from %s (attempt %d)", uri, attempt)
                t0 = time.time()
                c = s3util.client()
                n = s3util.download_prefix(c, bucket, prefix, MODEL_DIR)
                if n == 0:
                    raise RuntimeError(f"no objects under {uri}")
                log.warning("downloaded %d files from %s in %.1fs", n, uri, time.time() - t0)
                break
            except Exception as exc:
                log.warning("model download failed: %s", exc)
                time.sleep(5)
        else:
            log.error("giving up: model could not be downloaded; /readyz stays 503")
            return
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        torch.set_num_threads(1)  # the container is limited to 1 CPU core
        self.tok = AutoTokenizer.from_pretrained(MODEL_DIR)
        self.model = AutoModelForCausalLM.from_pretrained(MODEL_DIR, torch_dtype=torch.float32)
        self.model.eval()
        self._ready = True
        log.warning("model loaded: version=%s", os.environ.get("MODEL_VERSION"))

    def generate(self, text):
        import torch

        enc = self.tok(build_prompt(text), return_tensors="pt")
        with torch.inference_mode():
            out = self.model.generate(
                **enc,
                max_new_tokens=int(os.environ.get("MAX_NEW_TOKENS", "64")),
                do_sample=False,
                pad_token_id=self.tok.eos_token_id,
            )
        new = out[0][enc["input_ids"].shape[1]:]
        return self.tok.decode(new, skip_special_tokens=True).strip().split("\n")[0].strip()
