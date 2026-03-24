"""Type stubs for satsangi_pb2_grpc — gives autocomplete on request/context."""

import grpc
from app.generated import satsangi_pb2

class SatsangiServiceStub:
    CreateSatsangi: grpc.UnaryUnaryMultiCallable[
        satsangi_pb2.SatsangiCreate, satsangi_pb2.Satsangi
    ]
    SearchSatsangis: grpc.UnaryUnaryMultiCallable[
        satsangi_pb2.SearchRequest, satsangi_pb2.SatsangiList
    ]
    ListSatsangis: grpc.UnaryUnaryMultiCallable[
        satsangi_pb2.ListRequest, satsangi_pb2.SatsangiList
    ]
    Health: grpc.UnaryUnaryMultiCallable[
        satsangi_pb2.HealthRequest, satsangi_pb2.HealthResponse
    ]
    def __init__(self, channel: grpc.Channel) -> None: ...

class SatsangiServiceServicer:
    def CreateSatsangi(
        self,
        request: satsangi_pb2.SatsangiCreate,
        context: grpc.ServicerContext,
    ) -> satsangi_pb2.Satsangi: ...
    def SearchSatsangis(
        self,
        request: satsangi_pb2.SearchRequest,
        context: grpc.ServicerContext,
    ) -> satsangi_pb2.SatsangiList: ...
    def ListSatsangis(
        self,
        request: satsangi_pb2.ListRequest,
        context: grpc.ServicerContext,
    ) -> satsangi_pb2.SatsangiList: ...
    def Health(
        self,
        request: satsangi_pb2.HealthRequest,
        context: grpc.ServicerContext,
    ) -> satsangi_pb2.HealthResponse: ...

def add_SatsangiServiceServicer_to_server(
    servicer: SatsangiServiceServicer,
    server: grpc.Server,
) -> None: ...
