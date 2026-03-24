"""Shared fixtures for backend tests.

Tests hit a RUNNING server. Start it first:
  cd server && uv run task dev

Configure targets via env vars:
  PROXY_URL   = http://localhost:8080
  GRPC_TARGET = localhost:50051
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import grpc
import pytest

# Add server package so we can import generated protos
_SERVER_ROOT = Path(__file__).parent.parent.parent / "server"
sys.path.insert(0, str(_SERVER_ROOT))

from app.generated import satsangi_pb2, satsangi_pb2_grpc  # noqa: E402

PROXY_URL = os.environ.get("PROXY_URL", "http://localhost:8080")
GRPC_TARGET = os.environ.get("GRPC_TARGET", "localhost:50051")


@pytest.fixture(scope="session")
def grpc_channel():
    """Session-scoped gRPC channel."""
    ch = grpc.insecure_channel(GRPC_TARGET)
    yield ch
    ch.close()


@pytest.fixture(scope="session")
def stub(grpc_channel):
    """Session-scoped gRPC stub."""
    return satsangi_pb2_grpc.SatsangiServiceStub(grpc_channel)


@pytest.fixture
def proxy_url():
    return PROXY_URL
