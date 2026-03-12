"""FastAPI gateway that proxies REST requests to the gRPC backend.

Architecture:
  Browser  --HTTP/JSON-->  FastAPI gateway (:8000)  --gRPC/Protobuf-->  gRPC server (:50051)

This is the standard BFF (Backend-For-Frontend) pattern used in production
gRPC deployments.  The gateway translates REST↔gRPC so browsers can interact
with the system while all backend communication uses gRPC.
"""

import contextlib
import threading

import grpc
from fastapi import FastAPI

from app.generated import satsangi_pb2, satsangi_pb2_grpc
from app.grpc_server import serve as start_grpc_server
from app.models import Satsangi, SatsangiCreate

GRPC_TARGET = "localhost:50051"

# ---------------------------------------------------------------------------
# Lifecycle: start gRPC server in-process alongside FastAPI
# ---------------------------------------------------------------------------

_grpc_server = None


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    global _grpc_server
    _grpc_server = start_grpc_server(port=50051)
    yield
    if _grpc_server:
        _grpc_server.stop(grace=2)


app = FastAPI(title="JKP Registration POC (gRPC)", lifespan=lifespan)


def _get_stub():
    channel = grpc.insecure_channel(GRPC_TARGET)
    return satsangi_pb2_grpc.SatsangiServiceStub(channel)


def _proto_to_dict(pb) -> dict:
    """Convert a protobuf Satsangi message to a plain dict."""
    d: dict = {}
    for field in [
        "satsangi_id", "created_at", "first_name", "last_name", "phone_number",
        "nationality", "print_on_card", "country", "has_room_in_ashram",
        "banned", "first_timer",
    ]:
        d[field] = getattr(pb, field)
    for field in [
        "age", "date_of_birth", "pan", "gender", "special_category",
        "govt_id_type", "govt_id_number", "id_expiry_date", "id_issuing_country",
        "nick_name", "introducer", "address", "city", "district", "state",
        "pincode", "emergency_contact", "ex_center_satsangi_id", "introduced_by",
        "email", "date_of_first_visit", "notes",
    ]:
        if pb.HasField(field):
            d[field] = getattr(pb, field)
        else:
            d[field] = None
    return d


def _create_to_proto(data: SatsangiCreate) -> satsangi_pb2.SatsangiCreate:
    kwargs: dict = {
        "first_name": data.first_name,
        "last_name": data.last_name,
        "phone_number": data.phone_number,
        "nationality": data.nationality,
        "print_on_card": data.print_on_card,
        "country": data.country,
        "has_room_in_ashram": data.has_room_in_ashram,
        "banned": data.banned,
        "first_timer": data.first_timer,
    }
    for field in [
        "age", "date_of_birth", "pan", "gender", "special_category",
        "govt_id_type", "govt_id_number", "id_expiry_date", "id_issuing_country",
        "nick_name", "introducer", "address", "city", "district", "state",
        "pincode", "emergency_contact", "ex_center_satsangi_id", "introduced_by",
        "email", "date_of_first_visit", "notes",
    ]:
        val = getattr(data, field)
        if val is not None:
            kwargs[field] = val
    return satsangi_pb2.SatsangiCreate(**kwargs)


# ---------------------------------------------------------------------------
# REST endpoints (proxied to gRPC)
# ---------------------------------------------------------------------------


@app.post("/api/satsangis", response_model=Satsangi)
async def create_satsangi(data: SatsangiCreate):
    stub = _get_stub()
    proto_req = _create_to_proto(data)
    result = stub.CreateSatsangi(proto_req)
    return _proto_to_dict(result)


@app.get("/api/satsangis", response_model=list[Satsangi])
async def list_satsangis(q: str = ""):
    stub = _get_stub()
    if q:
        result = stub.SearchSatsangis(satsangi_pb2.SearchRequest(query=q))
    else:
        result = stub.ListSatsangis(satsangi_pb2.Empty())
    return [_proto_to_dict(s) for s in result.satsangis]
