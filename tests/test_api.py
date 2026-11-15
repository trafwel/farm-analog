import logging

import pytest
from fastapi.testclient import TestClient

from farm_analog import api, config, pipeline
from farm_analog.schema import AnalogResult, PolygonGeometry


def square(lon, lat, size=0.01):
    ring = [[lon, lat], [lon + size, lat], [lon + size, lat + size], [lon, lat + size], [lon, lat]]
    return {"type": "Polygon", "coordinates": [ring]}


COLFAX = square(-117.36, 46.88)  # inside the Palouse demo area


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("FARM_ANALOG_OFFLINE", "1")  # never call Earth Engine in tests
    api._cache.clear()
    return TestClient(api.app)


def test_health_reports_mode(client):
    assert client.get("/health").json() == {"status": "ok", "mode": "offline-demo"}


def test_palouse_field_gets_a_real_offline_result(client):
    response = client.post("/analogs", json={"field": COLFAX, "top_n": 5})
    assert response.status_code == 200
    result = AnalogResult.model_validate(response.json())
    assert result.source == "computed" and len(result.analogs) == 5
    assert result.field_id.startswith("field-") and result.notes
    assert result.analogs[0].sigma == pytest.approx(0.496, abs=1e-3)


def test_same_field_is_served_from_cache(client, monkeypatch):
    client.post("/analogs", json={"field": COLFAX})
    monkeypatch.setattr(pipeline, "analyze", lambda request: pytest.fail("not cached"))
    assert client.post("/analogs", json={"field": COLFAX}).status_code == 200


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ({"field": square(-100.0, 40.0)}, "Palouse demo area"),  # offline: outside Palouse
        ({"field": square(10.0, 50.0)}, "outside the area"),  # outside the US
        ({"field": square(-117.6, 46.8, size=0.5)}, "limit is"),  # far too big
        ({"field": COLFAX, "scenario": "ssp585"}, "only covers SSP2-4.5"),  # offline: one scenario
    ],
)
def test_unsupported_fields_get_a_clear_400(client, body, message):
    response = client.post("/analogs", json=body)
    assert response.status_code == 400
    assert message in response.json()["detail"]


def test_self_crossing_outline_is_rejected(client):
    bowtie = [
        [-117.36, 46.88],
        [-117.35, 46.89],
        [-117.35, 46.88],
        [-117.36, 46.89],
        [-117.36, 46.88],
    ]
    response = client.post("/analogs", json={"field": {"type": "Polygon", "coordinates": [bowtie]}})
    assert response.status_code == 400 and "crosses itself" in response.json()["detail"]


def test_malformed_request_is_a_422(client):
    assert client.post("/analogs", json={"field": COLFAX, "colour": "green"}).status_code == 422
    assert client.post("/analogs", json={"field": {"type": "Point"}}).status_code == 422


def test_failures_return_503_without_leaking_details_or_coordinates(client, monkeypatch, caplog):
    def boom(request):
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr(pipeline, "analyze", boom)
    with caplog.at_level(logging.ERROR):
        response = client.post("/analogs", json={"field": COLFAX})
    assert response.status_code == 503
    assert "secret" not in response.text
    assert "-117.36" not in caplog.text and "46.88" not in caplog.text


def test_cors_allows_only_the_frontend(client):
    allowed = client.options(
        "/analogs",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"},
    )
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:5173"
    other = client.options(
        "/analogs",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"},
    )
    assert "access-control-allow-origin" not in other.headers


def test_field_id_is_stable_and_hides_coordinates():
    field = PolygonGeometry.model_validate(COLFAX)
    assert pipeline.field_id(field) == pipeline.field_id(field)
    assert "117" not in pipeline.field_id(field)


def test_area_is_measured_on_the_ground():
    # 0.01° x 0.01° at 46.9° N is about 1.11 km x 0.76 km.
    area = pipeline.field_area_km2(PolygonGeometry.model_validate(COLFAX))
    assert area == pytest.approx(0.85, rel=0.05)
    assert area < config.MAX_FIELD_AREA_KM2


def test_mode_is_live_only_with_earth_engine(monkeypatch):
    monkeypatch.delenv("FARM_ANALOG_OFFLINE", raising=False)
    monkeypatch.delenv("EE_PROJECT", raising=False)
    assert pipeline.mode() == "offline-demo"
    monkeypatch.setenv("EE_PROJECT", "some-project")
    assert pipeline.mode() == "live"
