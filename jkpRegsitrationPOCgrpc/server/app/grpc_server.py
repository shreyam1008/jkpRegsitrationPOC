"""Pure gRPC server for JKP Satsangi Registration."""

import sys
import logging
from concurrent import futures
from pathlib import Path

import grpc
from grpc_reflection.v1alpha import reflection

# Ensure the server package is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.generated import satsangi_pb2
from app.generated import satsangi_pb2_grpc
from app import store
from app.models import SatsangiCreate

logger = logging.getLogger(__name__)


def _model_to_proto(s) -> satsangi_pb2.Satsangi:
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
    # Optional fields — only set if not None
    for field in [
        "age", "date_of_birth", "pan", "gender", "special_category",
        "govt_id_type", "govt_id_number", "id_expiry_date", "id_issuing_country",
        "nick_name", "introducer", "address", "city", "district", "state",
        "pincode", "emergency_contact", "ex_center_satsangi_id", "introduced_by",
        "email", "date_of_first_visit", "notes",
    ]:
        val = getattr(s, field)
        if val is not None:
            kwargs[field] = val
    return satsangi_pb2.Satsangi(**kwargs)


def _proto_to_create(req: satsangi_pb2.SatsangiCreate) -> SatsangiCreate:
    """Convert a protobuf SatsangiCreate message to a Pydantic model."""
    data: dict = {
        "first_name": req.first_name,
        "last_name": req.last_name,
        "phone_number": req.phone_number,
        "nationality": req.nationality if req.nationality else "Indian",
        "print_on_card": req.print_on_card,
        "country": req.country if req.country else "India",
        "has_room_in_ashram": req.has_room_in_ashram,
        "banned": req.banned,
        "first_timer": req.first_timer,
    }
    # Optional fields
    if req.HasField("age"):
        data["age"] = req.age
    for field in [
        "date_of_birth", "pan", "gender", "special_category",
        "govt_id_type", "govt_id_number", "id_expiry_date", "id_issuing_country",
        "nick_name", "introducer", "address", "city", "district", "state",
        "pincode", "emergency_contact", "ex_center_satsangi_id", "introduced_by",
        "email", "date_of_first_visit", "notes",
    ]:
        if req.HasField(field):
            data[field] = getattr(req, field)
    return SatsangiCreate(**data)


class SatsangiServiceServicer(satsangi_pb2_grpc.SatsangiServiceServicer):
    """Implements the SatsangiService gRPC service."""

    def CreateSatsangi(self, request, context):
        try:
            create_data = _proto_to_create(request)
            satsangi = store.create_satsangi(create_data)
            return _model_to_proto(satsangi)
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return satsangi_pb2.Satsangi()

    def SearchSatsangis(self, request, context):
        try:
            results = store.search_satsangis(request.query)
            return satsangi_pb2.SatsangiList(
                satsangis=[_model_to_proto(s) for s in results]
            )
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return satsangi_pb2.SatsangiList()

    def ListSatsangis(self, request, context):
        try:
            results = store.get_all_satsangis()
            return satsangi_pb2.SatsangiList(
                satsangis=[_model_to_proto(s) for s in results]
            )
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return satsangi_pb2.SatsangiList()

    def StreamSearchResults(self, request, context):
        """Server-streaming RPC: yields one Satsangi at a time."""
        try:
            results = store.search_satsangis(request.query)
            for s in results:
                yield _model_to_proto(s)
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))


def serve(port: int = 50051, max_workers: int = 10) -> grpc.Server:
    """Create, configure, and start the gRPC server."""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=max_workers))
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
    server.start()
    logger.info("gRPC server started on port %d", port)
    return server


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    s = serve()
    print(f"gRPC server listening on port 50051")
    try:
        s.wait_for_termination()
    except KeyboardInterrupt:
        s.stop(grace=2)
        print("\nServer stopped.")
