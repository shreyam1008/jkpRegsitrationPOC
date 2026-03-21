"""
grpc-web PROXY — bridges the browser to the gRPC server.

WHY THIS EXISTS:
  Browsers cannot speak native gRPC (no HTTP/2 framing, no trailers).
  So the browser sends "grpc-web" (base64-wrapped protobuf over HTTP/1.1),
  and this proxy translates it into real gRPC calls to :50051.

Architecture:
  Browser (React)  ──HTTP/1.1 POST──►  THIS PROXY (:8080)  ──gRPC/HTTP2──►  gRPC Server (:50051)

How grpc-web works:
  1. Browser wraps protobuf in a 5-byte frame: [flag:1][length:4][payload:N]
  2. Base64-encodes it (for HTTP/1.1 safety)
  3. POSTs to proxy with Content-Type: application/grpc-web-text
  4. Proxy decodes frame → forwards raw protobuf to gRPC server
  5. Proxy wraps gRPC response back in grpc-web frame → returns to browser
"""

import base64
import contextlib
import logging
import struct

import grpc
from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware

from app.grpc_server import serve as start_grpc_server

logger = logging.getLogger(__name__)

GRPC_TARGET = "localhost:50051"

# ─── Lifecycle: start gRPC server alongside the proxy ───

_grpc_server = None


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    global _grpc_server
    _grpc_server = start_grpc_server(port=50051)
    logger.info("gRPC server on :50051, proxy on :8080")
    yield
    if _grpc_server:
        _grpc_server.stop(grace=2)


app = FastAPI(title="gRPC-web Proxy (minimal demo)", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["grpc-status", "grpc-message"],
)


# ─── grpc-web frame helpers ───

def _decode_frame(raw: bytes) -> bytes:
    """Extract protobuf payload from grpc-web 5-byte frame."""
    if len(raw) < 5:
        raise ValueError("Frame too short")
    length = struct.unpack(">I", raw[1:5])[0]
    return raw[5: 5 + length]


def _encode_frame(payload: bytes, is_trailer: bool = False) -> bytes:
    """Wrap payload in a grpc-web frame."""
    flag = 0x80 if is_trailer else 0x00
    return struct.pack(">BI", flag, len(payload)) + payload


# ─── Single catch-all route for ALL grpc-web calls ───

@app.post("/{service_path:path}")
async def grpc_web_proxy(service_path: str, request: Request):
    """Proxy grpc-web request → native gRPC server.

    service_path example: jkp.demo.v1.DevoteeService/ListDevotees
    """
    content_type = request.headers.get("content-type", "")
    is_text = "grpc-web-text" in content_type

    # 1. Read raw body from browser
    body = await request.body()

    # 2. If base64-encoded (grpc-web-text), decode
    if is_text:
        body = base64.b64decode(body)

    # 3. Extract protobuf from grpc-web frame
    try:
        proto_payload = _decode_frame(body)
    except Exception:
        return Response(content=b"", status_code=400,
                        headers={"grpc-status": "3", "grpc-message": "Bad frame"})

    # 4. Forward to gRPC server over HTTP/2
    method = f"/{service_path}"
    channel = grpc.insecure_channel(GRPC_TARGET)
    try:
        response_bytes = channel.unary_unary(
            method,
            request_serializer=lambda x: x,     # already binary
            response_deserializer=lambda x: x,   # keep as binary
        )(proto_payload, timeout=30)
    except grpc.RpcError as e:
        status = str(e.code().value[0]) if hasattr(e, "code") else "13"
        msg = e.details() if hasattr(e, "details") else str(e)
        trailer = _encode_frame(f"grpc-status:{status}\r\ngrpc-message:{msg}\r\n".encode(), is_trailer=True)
        result = trailer
        if is_text:
            result = base64.b64encode(result)
        return Response(content=result,
                        media_type="application/grpc-web-text" if is_text else "application/grpc-web",
                        headers={"grpc-status": status, "grpc-message": msg})

    # 5. Wrap gRPC response back in grpc-web frame → return to browser
    data_frame = _encode_frame(response_bytes)
    trailer_frame = _encode_frame(b"grpc-status:0\r\ngrpc-message:OK\r\n", is_trailer=True)
    result = data_frame + trailer_frame
    if is_text:
        result = base64.b64encode(result)

    return Response(
        content=result,
        media_type="application/grpc-web-text" if is_text else "application/grpc-web",
        headers={"grpc-status": "0", "grpc-message": "OK"},
    )
