"""Command-parser web service.

POST /parse {"text": "..."} -> 200 + the 4-key JSON, headers X-Model-Version and X-Served-By
GET  /healthz               -> 200 while the process is alive
GET  /readyz                -> 503 until the model is loaded, then 200
Configuration: MODEL_URI, MODEL_VERSION, S3_ENDPOINT, MAX_NEW_TOKENS (+ FAULT_INJECT for validation tests).
S3 credentials come from AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY, injected from a Kubernetes Secret.
"""
import logging
import os
import socket
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from service.engine import Engine
from service.validate import validate_output

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
engine = Engine()


def _load_model():
    try:
        engine.load()
    except Exception:  # keep the process alive: /healthz stays 200, /readyz stays 503
        logging.getLogger("engine").exception("model loading failed")


@asynccontextmanager
async def lifespan(app):
    threading.Thread(target=_load_model, daemon=True).start()  # the server answers /healthz while loading
    yield


app = FastAPI(lifespan=lifespan)


class ParseRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1000)


def _headers():
    return {
        "X-Model-Version": os.environ.get("MODEL_VERSION", "unknown"),
        "X-Served-By": os.environ.get("HOSTNAME") or socket.gethostname(),  # in Kubernetes: the Pod name
    }


@app.get("/healthz")
async def healthz():
    return {"status": "alive"}


@app.get("/readyz")
async def readyz():
    if engine.ready:
        return {"status": "ready"}
    return JSONResponse({"status": "loading"}, status_code=503)


@app.post("/parse")
def parse(req: ParseRequest):
    if not engine.ready:
        return JSONResponse({"error": "model_not_ready"}, status_code=503, headers=_headers())
    raw = engine.generate(req.text)
    if os.environ.get("FAULT_INJECT") == "1":
        raw = "not json"
    obj = validate_output(raw)
    if obj is None:  # never return broken JSON with HTTP 200
        return JSONResponse({"error": "invalid_model_output"}, status_code=500, headers=_headers())
    return JSONResponse(obj, status_code=200, headers=_headers())
