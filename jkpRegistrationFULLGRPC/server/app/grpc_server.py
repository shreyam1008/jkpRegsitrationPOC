"""Async gRPC server for JKP Satsangi Registration with PostgreSQL backend.

This runs inside the same process as the grpc-web proxy (main.py).
All DB work goes through the shared async connection pool in db.py.

Fully async: grpc.aio server + async servicer methods + async DB (psycopg v3).
No ThreadPoolExecutor, no threads — everything runs on the event loop.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import grpc
import grpc.aio
from grpc_reflection.v1alpha import reflection

# Ensure the server package is importable when run standalone
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import store
from app.db import get_conn
from app.generated import satsangi_pb2, satsangi_pb2_grpc
from app.models import Satsangi as SatsangiModel
from app.models import SatsangiCreate

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Fields lists (computed once, reused in every conversion)
# ---------------------------------------------------------------------------

_OPTIONAL_FIELDS = (
    "age", "date_of_birth", "pan", "gender", "special_category",
    "govt_id_type", "govt_id_number", "id_expiry_date", "id_issuing_country",
    "nick_name", "introducer", "address", "city", "district", "state",
    "pincode", "emergency_contact", "ex_center_satsangi_id", "introduced_by",
    "email", "date_of_first_visit", "notes",
)

# ---------------------------------------------------------------------------
# Conversion helpers
# ---------------------------------------------------------------------------


def _model_to_proto(s: SatsangiModel) -> satsangi_pb2.Satsangi:
    """Convert a Pydantic Satsangi model to a protobuf Satsangi message."""
    kwargs = {
        "satsangi_id": s.satsangi_id,
        "created_at": s.created_at,
        "first_name": s.first_name,
        "last_name": s.last_name,
        "phone_number": s.phone_number,
        "nationality": s.nationality,
        "print_on_card": s.print_on_card,
        "country": s.country,
        "has_room_in_ashram": s.has_room_in_ashram,
        "banned": s.banned,
        "first_timer": s.first_timer,
    }
    for field in _OPTIONAL_FIELDS:
        val = getattr(s, field)
        if val is not None:
            kwargs[field] = val
    return satsangi_pb2.Satsangi(**kwargs)


def _proto_to_create(req: satsangi_pb2.SatsangiCreate) -> SatsangiCreate:
    """Convert a protobuf SatsangiCreate message to a Pydantic model."""
    data: dict[str, Any] = {
        "first_name": req.first_name,
        "last_name": req.last_name,
        "phone_number": req.phone_number,
        "nationality": req.nationality or "Indian",
        "print_on_card": req.print_on_card,
        "country": req.country or "India",
        "has_room_in_ashram": req.has_room_in_ashram,
        "banned": req.banned,
        "first_timer": req.first_timer,
    }
    if req.HasField("age"):
        data["age"] = req.age
    for field in _OPTIONAL_FIELDS:
        if field == "age":
            continue
        if req.HasField(field):
            data[field] = getattr(req, field)
    return SatsangiCreate(**data)


# ---------------------------------------------------------------------------
# Async gRPC service implementation
# ---------------------------------------------------------------------------


class SatsangiServiceServicer(satsangi_pb2_grpc.SatsangiServiceServicer):
    """Implements the SatsangiService gRPC service backed by PostgreSQL.

    All methods are async — they run on the event loop, never blocking threads.
    """

    async def CreateSatsangi(
        self,
        request: satsangi_pb2.SatsangiCreate,
        context: grpc.aio.ServicerContext,
    ) -> satsangi_pb2.Satsangi:
        try:
            create_data = _proto_to_create(request)
            satsangi = await store.create_satsangi(create_data)
            return _model_to_proto(satsangi)
        except Exception as e:
            logger.exception("CreateSatsangi failed")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return satsangi_pb2.Satsangi()

    async def SearchSatsangis(
        self,
        request: satsangi_pb2.SearchRequest,
        context: grpc.aio.ServicerContext,
    ) -> satsangi_pb2.SatsangiList:
        try:
            results, total = await store.search_satsangis(request.query)
            return satsangi_pb2.SatsangiList(
                satsangis=[_model_to_proto(s) for s in results],
                total_count=total,
            )
        except Exception as e:
            logger.exception("SearchSatsangis failed")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return satsangi_pb2.SatsangiList()

    async def ListSatsangis(
        self,
        request: satsangi_pb2.ListRequest,
        context: grpc.aio.ServicerContext,
    ) -> satsangi_pb2.SatsangiList:
        try:
            limit = request.limit if request.limit > 0 else 0
            offset = request.offset if request.offset > 0 else 0
            results, total = await store.get_all_satsangis(limit=limit, offset=offset)
            return satsangi_pb2.SatsangiList(
                satsangis=[_model_to_proto(s) for s in results],
                total_count=total,
            )
        except Exception as e:
            logger.exception("ListSatsangis failed")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return satsangi_pb2.SatsangiList()

    async def Health(
        self,
        request: satsangi_pb2.HealthRequest,
        context: grpc.aio.ServicerContext,
    ) -> satsangi_pb2.HealthResponse:
        db_ok = "unknown"
        try:
            async with get_conn() as conn:
                await conn.execute("SELECT 1")
            db_ok = "connected"
        except Exception:
            db_ok = "disconnected"
        return satsangi_pb2.HealthResponse(
            status="healthy",
            timestamp=datetime.now().isoformat(),
            message="Service is running",
            db_status=db_ok,
        )


# ---------------------------------------------------------------------------
# Async server factory
# ---------------------------------------------------------------------------


async def serve(port: int = 50051) -> grpc.aio.Server:
    """Create, configure, and start the async gRPC server."""
    server = grpc.aio.server()
    satsangi_pb2_grpc.add_SatsangiServiceServicer_to_server(
        SatsangiServiceServicer(), server
    )

    # Enable server reflection (for tools like grpcurl, grpcui, Postman)
    service_names = (
        satsangi_pb2.DESCRIPTOR.services_by_name["SatsangiService"].full_name,
        reflection.SERVICE_NAME,
    )
    reflection.enable_server_reflection(service_names, server)

    server.add_insecure_port(f"[::]:{port}")
    await server.start()
    logger.info("Async gRPC server started on port %d", port)
    return server


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from app.db import close_pool, init_pool

    async def main() -> None:
        await init_pool()
        s = await serve()
        print("Async gRPC server listening on port 50051")
        try:
            await s.wait_for_termination()
        except KeyboardInterrupt:
            await s.stop(grace=2)
            await close_pool()
            print("\nServer stopped.")

    asyncio.run(main())
