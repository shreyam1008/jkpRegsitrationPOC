"""grpc-web proxy: translates the grpc-web wire format from browsers into
native gRPC calls to the backend server on :50051.

Architecture (NO REST anywhere):
  Browser (React + grpc-web)  --grpc-web/HTTP1.1-->  Proxy (:8080)  --gRPC/HTTP2-->  gRPC Server (:50051)  --SQL-->  PostgreSQL

The grpc-web protocol is a subset of gRPC designed for browsers:
- Content-Type: application/grpc-web-text (base64) or application/grpc-web (binary)
- 5-byte frame header: [compressed(1 byte)] [length(4 bytes big-endian)] [payload]
- Trailers sent as a final frame with compressed flag = 0x80

This proxy handles all of that so the browser talks gRPC end-to-end.
"""

import base64
import contextlib
import logging
import struct

import grpc
from fastapi import FastAPI, Request
from fastapi.responses import Response

from app.grpc_server import serve as start_grpc_server

logger = logging.getLogger(__name__)

GRPC_TARGET = "localhost:50051"

# ---------------------------------------------------------------------------
# Lifecycle: start gRPC server in-process alongside the proxy
# ---------------------------------------------------------------------------

_grpc_server = None


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    global _grpc_server
    _grpc_server = start_grpc_server(port=50051)
    logger.info("gRPC server started on :50051, grpc-web proxy on :8080")
    yield
    if _grpc_server:
        _grpc_server.stop(grace=2)


app = FastAPI(title="JKP Registration POC — grpc-web Proxy", lifespan=lifespan)


# ---------------------------------------------------------------------------
# CORS — required for grpc-web from browsers
# ---------------------------------------------------------------------------

from fastapi.middleware.cors import CORSMiddleware

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
    """Extract the protobuf payload from a grpc-web frame (5-byte header + data)."""
    if len(raw) < 5:
        raise ValueError("grpc-web frame too short")
    _compressed = raw[0]
    length = struct.unpack(">I", raw[1:5])[0]
    return raw[5 : 5 + length]


def _encode_grpc_web_frame(payload: bytes, is_trailer: bool = False) -> bytes:
    """Wrap a protobuf payload in a grpc-web frame."""
    flag = 0x80 if is_trailer else 0x00
    header = struct.pack(">BI", flag, len(payload))
    return header + payload


# ---------------------------------------------------------------------------
# Single catch-all POST route that handles ALL grpc-web calls
# ---------------------------------------------------------------------------

@app.post("/{service_path:path}")
async def grpc_web_proxy(service_path: str, request: Request):
    """Proxy a grpc-web request to the native gRPC server.

    The service_path matches patterns like:
      jkp.registration.v1.SatsangiService/CreateSatsangi
      jkp.registration.v1.SatsangiService/SearchSatsangis
      jkp.registration.v1.SatsangiService/ListSatsangis
    """
    content_type = request.headers.get("content-type", "")
    is_text = "grpc-web-text" in content_type

    # Read the raw body
    body = await request.body()

    # If grpc-web-text, base64-decode it
    if is_text:
        body = base64.b64decode(body)

    # Extract the protobuf payload from the grpc-web frame
    try:
        proto_payload = _decode_grpc_web_frame(body)
    except Exception:
        return Response(
            content=b"",
            status_code=400,
            headers={"grpc-status": "3", "grpc-message": "Invalid grpc-web frame"},
        )

    # Build the full gRPC method path
    method = f"/{service_path}"

    # Forward to the native gRPC server
    channel = grpc.insecure_channel(GRPC_TARGET)
    try:
        response_future = channel.unary_unary(
            method,
            request_serializer=lambda x: x,    # already serialized
            response_deserializer=lambda x: x,  # return raw bytes
        )(proto_payload, timeout=30)
    except grpc.RpcError as e:
        status_code = str(e.code().value[0]) if hasattr(e, "code") else "13"
        message = e.details() if hasattr(e, "details") else str(e)
        trailers = f"grpc-status:{status_code}\r\ngrpc-message:{message}\r\n"
        trailer_frame = _encode_grpc_web_frame(trailers.encode(), is_trailer=True)
        data_frame = b""
        result = data_frame + trailer_frame
        if is_text:
            result = base64.b64encode(result)
        return Response(
            content=result,
            media_type="application/grpc-web-text" if is_text else "application/grpc-web",
            headers={"grpc-status": status_code, "grpc-message": message},
        )

    # Build the grpc-web response: data frame + trailer frame
    data_frame = _encode_grpc_web_frame(response_future)
    trailers = "grpc-status:0\r\ngrpc-message:OK\r\n"
    trailer_frame = _encode_grpc_web_frame(trailers.encode(), is_trailer=True)
    result = data_frame + trailer_frame

    if is_text:
        result = base64.b64encode(result)

    resp_content_type = "application/grpc-web-text" if is_text else "application/grpc-web"
    return Response(
        content=result,
        media_type=resp_content_type,
        headers={"grpc-status": "0", "grpc-message": "OK"},
    )
