"""CreateSatsangi tests — gRPC direct + grpc-web proxy."""

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

def _grpc_web_create(first: str, last: str, phone: str) -> httpx.Response:
    """Send a CreateSatsangi via the grpc-web proxy."""
    req = satsangi_pb2.SatsangiCreate(
        first_name=first,
        last_name=last,
        phone_number=phone,
        nationality="Indian",
        country="India",
    )
    payload = req.SerializeToString()
    frame = struct.pack(">BI", 0x00, len(payload)) + payload

    return httpx.post(
        f"{PROXY_URL}/jkp.registration.v1.SatsangiService/CreateSatsangi",
        content=base64.b64encode(frame),
        headers={"content-type": "application/grpc-web-text", "x-grpc-web": "1"},
    )


# ---------------------------------------------------------------------------
# gRPC direct
# ---------------------------------------------------------------------------

class TestCreateDirect:
    """CreateSatsangi via native gRPC on :50051."""

    def test_returns_id(self, stub):
        resp = stub.CreateSatsangi(satsangi_pb2.SatsangiCreate(
            first_name="DirectTest",
            last_name="User",
            phone_number="9000000001",
            nationality="Indian",
            country="India",
        ))
        assert len(resp.satsangi_id) == 8
        assert resp.first_name == "DirectTest"

    def test_sets_defaults(self, stub):
        resp = stub.CreateSatsangi(satsangi_pb2.SatsangiCreate(
            first_name="DefaultTest",
            last_name="User",
            phone_number="9000000002",
            nationality="Indian",
            country="India",
        ))
        assert resp.banned is False
        assert resp.first_timer is False
        assert resp.has_room_in_ashram is False

    def test_optional_fields(self, stub):
        resp = stub.CreateSatsangi(satsangi_pb2.SatsangiCreate(
            first_name="OptionalTest",
            last_name="User",
            phone_number="9000000003",
            nationality="Indian",
            country="India",
            age=30,
            gender="Male",
            city="Mangarh",
            email="test@example.com",
        ))
        assert resp.age == 30
        assert resp.gender == "Male"
        assert resp.city == "Mangarh"
        assert resp.email == "test@example.com"


# ---------------------------------------------------------------------------
# grpc-web proxy
# ---------------------------------------------------------------------------

class TestCreateProxy:
    """CreateSatsangi via grpc-web proxy on :8080."""

    def test_returns_grpc_status_0(self):
        resp = _grpc_web_create("ProxyTest", "User", "9000000010")
        assert resp.status_code == 200
        assert resp.headers.get("grpc-status") == "0"

    def test_response_has_body(self):
        resp = _grpc_web_create("ProxyBody", "User", "9000000011")
        raw = base64.b64decode(resp.content)
        assert len(raw) > 5, "Should have data frame + trailer"

    def test_bad_frame_returns_400(self):
        resp = httpx.post(
            f"{PROXY_URL}/jkp.registration.v1.SatsangiService/CreateSatsangi",
            content=base64.b64encode(b"\x00\x01"),
            headers={"content-type": "application/grpc-web-text", "x-grpc-web": "1"},
        )
        assert resp.status_code == 400
