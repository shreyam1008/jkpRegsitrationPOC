"""grpc-web proxy — translates grpc-web wire format into native gRPC.

Architecture:
  Browser (ConnectRPC grpc-web)
      ↓  HTTP/1.1 POST  (grpc-web-text, base64)
  Caddy (TLS + compression + HTTP/3)
      ↓  HTTP/1.1 reverse_proxy
  THIS PROXY  (:8080, uvicorn async)
      ↓  HTTP/2 multiplexed via singleton channel
  gRPC SERVER (:50051, in-process, ThreadPoolExecutor)
      ↓  pooled connection
  PostgreSQL

Performance notes:
  • Singleton gRPC channel — one TCP conn, HTTP/2 multiplexes all RPCs
  • DB connection pool — 2–20 conns, zero connect overhead per request
  • Pre-built OK trailer — allocated once, reused every successful response
  • Identity serializers — no copy, pass raw protobuf bytes through
  • Single uvicorn process — no fork, no port clash on :50051
"""

from __future__ import annotations

import base64
import contextlib
import logging
import struct
from collections.abc import AsyncIterator

import grpc
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from app.db import close_pool, init_pool
from app.grpc_server import serve as start_grpc_server

logger = logging.getLogger(__name__)

GRPC_TARGET = "localhost:50051"

# ---------------------------------------------------------------------------
# Pre-allocated constants (avoid re-creating on every request)
# ---------------------------------------------------------------------------

_OK_TRAILERS = b"grpc-status:0\r\ngrpc-message:OK\r\n"
_OK_TRAILER_FRAME = struct.pack(">BI", 0x80, len(_OK_TRAILERS)) + _OK_TRAILERS

def _identity(x: bytes) -> bytes:
    return x

# ---------------------------------------------------------------------------
# Singleton gRPC channel — created once, reused for every request.
# ---------------------------------------------------------------------------

_channel: grpc.Channel | None = None


def _get_channel() -> grpc.Channel:  # noqa: RUF036
    global _channel
    if _channel is None:
        _channel = grpc.insecure_channel(
            GRPC_TARGET,
            options=[
                ("grpc.keepalive_time_ms", 30_000),
                ("grpc.keepalive_timeout_ms", 5_000),
                ("grpc.keepalive_permit_without_calls", 1),
            ],
        )
    return _channel


# ---------------------------------------------------------------------------
# Lifecycle: DB pool → gRPC server → channel  (all created once at startup)
# ---------------------------------------------------------------------------

_grpc_server: grpc.Server | None = None


@contextlib.asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    global _grpc_server, _channel
    init_pool(minconn=2, maxconn=20)
    _grpc_server = start_grpc_server(port=50051)
    _channel = _get_channel()
    logger.info("Ready — pool(2-20) + gRPC(:50051) + proxy(:8080)")
    yield
    if _grpc_server:
        _grpc_server.stop(grace=2)
    if _channel:
        _channel.close()
        _channel = None
    close_pool()


app = FastAPI(title="JKP Registration — grpc-web Proxy", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=[
        "grpc-status", "grpc-message", "grpc-encoding",
        "grpc-accept-encoding", "x-grpc-web",
    ],
)

# ---------------------------------------------------------------------------
# grpc-web frame helpers
# ---------------------------------------------------------------------------


def _decode_grpc_web_frame(raw: bytes) -> bytes:
    """Extract protobuf payload from a grpc-web frame (5-byte header + data)."""
    if len(raw) < 5:
        raise ValueError("grpc-web frame too short")
    length = struct.unpack(">I", raw[1:5])[0]
    return raw[5 : 5 + length]


def _encode_data_frame(payload: bytes) -> bytes:
    """Wrap protobuf payload in a grpc-web DATA frame (flag=0x00)."""
    return struct.pack(">BI", 0x00, len(payload)) + payload


# ---------------------------------------------------------------------------
# Health check — Caddy polls this to verify the backend is alive
# ---------------------------------------------------------------------------

@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Catch-all POST: proxy every grpc-web call to the in-process gRPC server
# ---------------------------------------------------------------------------

@app.post("/{service_path:path}")
async def grpc_web_proxy(service_path: str, request: Request) -> Response:
    content_type = request.headers.get("content-type", "")
    is_text = "grpc-web-text" in content_type

    body = await request.body()

    if is_text:
        body = base64.b64decode(body)

    try:
        proto_payload = _decode_grpc_web_frame(body)
    except Exception:
        return Response(
            content=b"",
            status_code=400,
            headers={"grpc-status": "3", "grpc-message": "Invalid grpc-web frame"},
        )

    channel = _get_channel()
    try:
        response_bytes = channel.unary_unary(
            f"/{service_path}",
            request_serializer=_identity,
            response_deserializer=_identity,
        )(proto_payload, timeout=30)
    except grpc.RpcError as e:
        code = str(e.code().value[0]) if hasattr(e, "code") else "13"
        msg = e.details() if hasattr(e, "details") else str(e)
        trailer_text = f"grpc-status:{code}\r\ngrpc-message:{msg}\r\n".encode()
        trailer_frame = struct.pack(">BI", 0x80, len(trailer_text)) + trailer_text
        result = trailer_frame
        if is_text:
            result = base64.b64encode(result)
        return Response(
            content=result,
            media_type="application/grpc-web-text" if is_text else "application/grpc-web",
            headers={"grpc-status": code, "grpc-message": msg},
        )

    result = _encode_data_frame(response_bytes) + _OK_TRAILER_FRAME
    if is_text:
        result = base64.b64encode(result)

    return Response(
        content=result,
        media_type="application/grpc-web-text" if is_text else "application/grpc-web",
        headers={"grpc-status": "0", "grpc-message": "OK"},
    )
