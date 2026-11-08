import json

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

import service.app as appmod  # noqa: E402


class Stub:
    """Stands in for the real model so the API contract can be tested without PyTorch."""
    def __init__(self, ready=True, reply='{"intent": "alarm_set", "date": "tomorrow", "time": "seven am", "place": null}'):
        self._ready, self.reply = ready, reply

    ready = property(lambda self: self._ready)

    def load(self):
        pass

    def generate(self, text):
        return self.reply


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("MODEL_VERSION", "v-test")
    monkeypatch.setenv("HOSTNAME", "pod-abc")
    monkeypatch.delenv("FAULT_INJECT", raising=False)
    monkeypatch.setattr(appmod, "engine", Stub())
    with TestClient(appmod.app) as c:
        yield c


def test_parse_returns_exact_json_and_headers(client):
    r = client.post("/parse", json={"text": "set an alarm for seven am tomorrow"})
    assert r.status_code == 200
    assert r.json() == {"intent": "alarm_set", "date": "tomorrow", "time": "seven am", "place": None}
    assert r.headers["X-Model-Version"] == "v-test" and r.headers["X-Served-By"] == "pod-abc"


def test_healthz_always_ok_and_readyz_503_until_loaded(client, monkeypatch):
    assert client.get("/healthz").status_code == 200
    assert client.get("/readyz").status_code == 200
    monkeypatch.setattr(appmod, "engine", Stub(ready=False))
    assert client.get("/healthz").status_code == 200
    assert client.get("/readyz").status_code == 503
    assert client.post("/parse", json={"text": "hi"}).status_code == 503


def test_fault_injection_gives_500_with_exact_body(client, monkeypatch):
    monkeypatch.setenv("FAULT_INJECT", "1")
    r = client.post("/parse", json={"text": "anything"})
    assert r.status_code == 500 and r.json() == {"error": "invalid_model_output"}


def test_broken_model_output_never_returns_200(client, monkeypatch):
    monkeypatch.setattr(appmod, "engine", Stub(reply='{"intent": "alarm_set", "da'))
    r = client.post("/parse", json={"text": "x"})
    assert r.status_code == 500 and r.json() == {"error": "invalid_model_output"}
    assert json.loads(r.text) == {"error": "invalid_model_output"}
