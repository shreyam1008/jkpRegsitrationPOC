"""
Minimal gRPC server — ONE service, ONE method: ListDevotees.

Reads directly from the `devotees` table in PostgreSQL (jkp_reg_poc_rest).
Same database the REST POC uses, so you see the same data in both.

Architecture:
  Browser ──grpc-web──► Proxy (:8080) ──gRPC/HTTP2──► THIS SERVER (:50051) ──SQL──► PostgreSQL
"""

import logging
from concurrent import futures

import grpc
import psycopg2
import psycopg2.extras
from grpc_reflection.v1alpha import reflection

from app.generated import devotee_pb2
from app.generated import devotee_pb2_grpc

logger = logging.getLogger(__name__)

# ─── Database config (same DB as the REST POC) ───
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "jkp_reg_poc_rest",
    "user": "postgres",
    "password": "postgres",
}


def _fetch_all_devotees() -> list[dict]:
    """Plain SQL query — fetch all devotees, newest first."""
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT id, satsangi_id, first_name, last_name, phone_number,
                       gender, age, city, state, nationality, created_at
                FROM devotees
                ORDER BY created_at DESC
            """)
            return cur.fetchall()
    finally:
        conn.close()


def _row_to_proto(row: dict) -> devotee_pb2.Devotee:
    """Convert a database row → protobuf Devotee message.

    This is the key translation layer:
      DB dict  →  protobuf object  →  (library serializes to binary automatically)
    """
    kwargs = {
        "id": row["id"],
        "satsangi_id": row["satsangi_id"],
        "first_name": row["first_name"],
        "last_name": row["last_name"],
        "phone_number": row["phone_number"],
        "nationality": row["nationality"] or "Indian",
        "created_at": row["created_at"].isoformat() if row["created_at"] else "",
    }
    # Optional fields — only set if not None (protobuf skips unset optionals)
    if row.get("gender"):
        kwargs["gender"] = row["gender"]
    if row.get("age") is not None:
        kwargs["age"] = row["age"]
    if row.get("city"):
        kwargs["city"] = row["city"]
    if row.get("state"):
        kwargs["state"] = row["state"]

    return devotee_pb2.Devotee(**kwargs)


# ─── gRPC Service Implementation ───

class DevoteeServiceServicer(devotee_pb2_grpc.DevoteeServiceServicer):
    """Implements the DevoteeService defined in devotee.proto.

    Just ONE method: ListDevotees.
    gRPC framework handles all the binary serialization / HTTP/2 framing.
    You only write business logic here.
    """

    def ListDevotees(self, request, context):
        """Called when a client sends an Empty message to ListDevotees RPC.

        Returns a DevoteeList containing all devotees from PostgreSQL.
        """
        logger.info("ListDevotees called")
        try:
            rows = _fetch_all_devotees()
            devotees = [_row_to_proto(row) for row in rows]
            logger.info("Returning %d devotees", len(devotees))
            return devotee_pb2.DevoteeList(devotees=devotees)
        except Exception as e:
            logger.exception("ListDevotees failed")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return devotee_pb2.DevoteeList()


# ─── Server startup ───

def serve(port: int = 50051) -> grpc.Server:
    """Create and start the gRPC server on the given port."""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))

    # Register our service implementation
    devotee_pb2_grpc.add_DevoteeServiceServicer_to_server(
        DevoteeServiceServicer(), server
    )

    # Enable reflection (so tools like grpcurl can discover services)
    service_names = (
        devotee_pb2.DESCRIPTOR.services_by_name["DevoteeService"].full_name,
        reflection.SERVICE_NAME,
    )
    reflection.enable_server_reflection(service_names, server)

    server.add_insecure_port(f"[::]:{port}")
    server.start()
    logger.info("gRPC server listening on :%d", port)
    return server


# Run standalone: uv run python -m app.grpc_server
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    s = serve()
    print("gRPC server listening on :50051  (Ctrl+C to stop)")
    try:
        s.wait_for_termination()
    except KeyboardInterrupt:
        s.stop(grace=2)
        print("\nStopped.")
