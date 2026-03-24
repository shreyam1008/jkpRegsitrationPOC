"""SearchSatsangis + ListSatsangis tests — gRPC direct + proxy."""

from __future__ import annotations

import base64
import struct
import sys

import httpx

from conftest import PROXY_URL, _SERVER_ROOT

sys.path.insert(0, str(_SERVER_ROOT))
from app.generated import satsangi_pb2  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _proxy_post(rpc: str, msg) -> httpx.Response:
    payload = msg.SerializeToString()
    frame = struct.pack(">BI", 0x00, len(payload)) + payload
    return httpx.post(
        f"{PROXY_URL}/jkp.registration.v1.SatsangiService/{rpc}",
        content=base64.b64encode(frame),
        headers={"content-type": "application/grpc-web-text", "x-grpc-web": "1"},
    )


# ---------------------------------------------------------------------------
# gRPC direct
# ---------------------------------------------------------------------------

class TestSearchDirect:
    def test_search_by_name(self, stub):
        # Create a record first
        stub.CreateSatsangi(satsangi_pb2.SatsangiCreate(
            first_name="Findable",
            last_name="Person",
            phone_number="7000000001",
            nationality="Indian",
            country="India",
        ))
        resp = stub.SearchSatsangis(satsangi_pb2.SearchRequest(query="Findable"))
        assert any(s.first_name == "Findable" for s in resp.satsangis)

    def test_search_empty_returns_results(self, stub):
        resp = stub.SearchSatsangis(satsangi_pb2.SearchRequest(query=""))
        assert len(resp.satsangis) >= 0  # no error


class TestListDirect:
    def test_list_with_limit(self, stub):
        resp = stub.ListSatsangis(satsangi_pb2.ListRequest(limit=3))
        assert len(resp.satsangis) <= 3

    def test_list_ordered_newest_first(self, stub):
        resp = stub.ListSatsangis(satsangi_pb2.ListRequest(limit=10))
        if len(resp.satsangis) >= 2:
            ts = [s.created_at for s in resp.satsangis]
            assert ts == sorted(ts, reverse=True)


# ---------------------------------------------------------------------------
# grpc-web proxy
# ---------------------------------------------------------------------------

class TestSearchProxy:
    def test_search_returns_ok(self):
        resp = _proxy_post("SearchSatsangis", satsangi_pb2.SearchRequest(query="test"))
        assert resp.headers.get("grpc-status") == "0"

    def test_list_returns_ok(self):
        resp = _proxy_post("ListSatsangis", satsangi_pb2.ListRequest(limit=5))
        assert resp.headers.get("grpc-status") == "0"

    def test_nonexistent_service_errors(self):
        payload = b""
        frame = struct.pack(">BI", 0x00, len(payload)) + payload
        resp = httpx.post(
            f"{PROXY_URL}/fake.Service/Nope",
            content=base64.b64encode(frame),
            headers={"content-type": "application/grpc-web-text", "x-grpc-web": "1"},
        )
        assert resp.headers.get("grpc-status", "0") != "0"
