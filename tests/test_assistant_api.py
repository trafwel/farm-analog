"""Bill's API endpoints, with a fake Gemini client (no network)."""

import json
import logging

import pytest
from assistant_fakes import FakeLLM, load_result
from fastapi.testclient import TestClient

from farm_analog import api
from farm_analog.contract import CONTRACT_DIR

COLFAX = load_result("fake-colfax")
FARMER_TEXT = "We farm 800 acres of dryland wheat near Colfax; drought worries me."


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("FARM_ANALOG_OFFLINE", "1")  # never call Earth Engine in tests
    api._summary_cache.clear()
    return TestClient(api.app)


def use_llm(monkeypatch, llm):
    monkeypatch.setattr(api, "bill_llm", llm)
    return llm


def test_parse_returns_validated_fields(client, monkeypatch):
    use_llm(monkeypatch, FakeLLM({"crops": ["wheat"], "acres": 800, "irrigated": False,
                                  "worries": ["drought"]}))
    body = client.post("/bill/parse", json={"text": FARMER_TEXT}).json()
    assert body["ok"] is True
    assert body["profile"]["acres"] == 800 and body["profile"]["worries"] == ["drought"]


def test_parse_without_a_key_says_so(client, monkeypatch):
    use_llm(monkeypatch, None)
    body = client.post("/bill/parse", json={"text": FARMER_TEXT}).json()
    assert body["ok"] is False and "no Gemini key" in body["error"]
    assert body["profile"]["crops"] == []


def test_parse_rejects_oversized_or_unknown_input(client, monkeypatch):
    use_llm(monkeypatch, FakeLLM({}))
    too_long = "x" * (api.MAX_BILL_TEXT_CHARS + 1)
    assert client.post("/bill/parse", json={"text": too_long}).status_code == 422
    assert client.post("/bill/parse", json={"text": "hi", "role": "admin"}).status_code == 422


def test_parse_bad_model_output_is_not_a_server_error(client, monkeypatch):
    use_llm(monkeypatch, FakeLLM("not json"))
    response = client.post("/bill/parse", json={"text": FARMER_TEXT})
    assert response.status_code == 200 and response.json()["ok"] is False


def test_summary_without_a_key_uses_the_template(client, monkeypatch):
    use_llm(monkeypatch, None)
    body = client.post("/bill/summary", json=COLFAX.model_dump(mode="json")).json()
    assert body["source"] == "template"
    assert body["text"].startswith("Demo data:")


def test_summary_is_cached_by_result(client, monkeypatch):
    llm = use_llm(monkeypatch, FakeLLM("The closest place today is Example area 1."))
    first = client.post("/bill/summary", json=COLFAX.model_dump(mode="json")).json()
    second = client.post("/bill/summary", json=COLFAX.model_dump(mode="json")).json()
    assert first == second and first["source"] == "gemini"
    assert len(llm.calls) == 1
    other = COLFAX.model_copy(update={"field_id": "fake-other"})
    client.post("/bill/summary", json=other.model_dump(mode="json"))
    assert len(llm.calls) == 2


def test_gemini_outage_is_not_cached(client, monkeypatch):
    llm = use_llm(monkeypatch, FakeLLM(error=True))
    for _ in range(2):
        body = client.post("/bill/summary", json=COLFAX.model_dump(mode="json")).json()
        assert body["source"] == "template"
    assert len(llm.calls) == 2  # retried, not served a stale fallback


def test_summary_of_a_live_offline_result(client, monkeypatch):
    # The real pipeline's offline result (not the fixture) summarizes without a demo notice.
    use_llm(monkeypatch, None)
    ring = [[-117.36, 46.88], [-117.35, 46.88], [-117.35, 46.89], [-117.36, 46.89],
            [-117.36, 46.88]]
    result = client.post("/analogs", json={"field": {"type": "Polygon", "coordinates": [ring]},
                                           "top_n": 5}).json()
    body = client.post("/bill/summary", json=result).json()
    assert body["source"] == "template" and body["notices"] == []
    assert "Average temperature, today to future" in body["text"]


def test_invalid_result_is_rejected(client):
    bad = json.loads(COLFAX.model_dump_json())
    bad["analogs"][0]["match_quality"] = "none"  # contradicts its sigma
    assert client.post("/bill/summary", json=bad).status_code == 422


def test_farmer_text_and_coordinates_are_never_logged(client, monkeypatch, caplog):
    use_llm(monkeypatch, FakeLLM(error=True))
    caplog.set_level(logging.DEBUG)
    client.post("/bill/parse", json={"text": FARMER_TEXT})
    client.post("/bill/summary", json=COLFAX.model_dump(mode="json"))
    logged = caplog.text
    assert "Colfax" not in logged and "800 acres" not in logged
    assert str(COLFAX.analogs[0].lon) not in logged and str(COLFAX.analogs[0].lat) not in logged


def test_bill_models_stay_out_of_the_contract():
    # The frontend's types are generated from contract/; Bill's models must not change them.
    for path in CONTRACT_DIR.glob("*.schema.json"):
        text = path.read_text(encoding="utf-8")
        assert "BillSummary" not in text and "ParseResult" not in text
    paths = TestClient(api.app).get("/openapi.json").json()["paths"]
    assert "/bill/parse" in paths and "/bill/summary" in paths
