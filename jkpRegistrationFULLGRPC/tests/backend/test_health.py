"""Health endpoint + Health RPC tests."""

from __future__ import annotations

import httpx

from conftest import PROXY_URL, _SERVER_ROOT  # noqa: F401

import sys
sys.path.insert(0, str(_SERVER_ROOT))
from app.generated import satsangi_pb2  # noqa: E402


class TestHealthEndpoint:
    """GET /healthz — polled by Caddy."""

    def test_returns_ok(self):
        resp = httpx.get(f"{PROXY_URL}/healthz")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_responds_fast(self):
        resp = httpx.get(f"{PROXY_URL}/healthz")
        assert resp.elapsed.total_seconds() < 0.1


class TestHealthRPC:
    """Health RPC via gRPC direct."""

    def test_returns_healthy(self, stub):
        resp = stub.Health(satsangi_pb2.HealthRequest())
        assert resp.status == "healthy"
        assert resp.message == "Service is running"

    def test_reports_db_status(self, stub):
        resp = stub.Health(satsangi_pb2.HealthRequest())
        assert resp.db_status in ("connected", "disconnected")

    def test_has_timestamp(self, stub):
        resp = stub.Health(satsangi_pb2.HealthRequest())
        assert len(resp.timestamp) > 0
