/**
 * gRPC-web service client for SatsangiService.
 *
 * Uses the grpc-web library to make real gRPC calls from the browser
 * through the grpc-web proxy on :8080.
 */

import * as grpcWeb from 'grpc-web'
import { SatsangiCreate, SatsangiMsg, SatsangiList, SearchRequest, Empty } from './satsangi_pb'

const SERVICE_NAME = 'jkp.registration.v1.SatsangiService'

export class SatsangiServiceClient {
  private client: grpcWeb.AbstractClientBase
  private hostname: string

  constructor(hostname: string, _credentials: null = null, options: grpcWeb.GrpcWebClientBaseOptions = {}) {
    this.hostname = hostname
    this.client = new grpcWeb.GrpcWebClientBase(options)
  }

  createSatsangi(
    request: SatsangiCreate,
    metadata?: grpcWeb.Metadata,
  ): Promise<SatsangiMsg> {
    const methodDescriptor = new grpcWeb.MethodDescriptor<SatsangiCreate, SatsangiMsg>(
      `/${SERVICE_NAME}/CreateSatsangi`,
      grpcWeb.MethodType.UNARY,
      SatsangiCreate,
      SatsangiMsg,
      (req: SatsangiCreate) => req.serializeBinary(),
      SatsangiMsg.deserializeBinary,
    )

    return this.client.thenableCall(
      this.hostname + methodDescriptor.getName(),
      request,
      metadata || {},
      methodDescriptor,
    )
  }

  searchSatsangis(
    request: SearchRequest,
    metadata?: grpcWeb.Metadata,
  ): Promise<SatsangiList> {
    const methodDescriptor = new grpcWeb.MethodDescriptor<SearchRequest, SatsangiList>(
      `/${SERVICE_NAME}/SearchSatsangis`,
      grpcWeb.MethodType.UNARY,
      SearchRequest,
      SatsangiList,
      (req: SearchRequest) => req.serializeBinary(),
      SatsangiList.deserializeBinary,
    )

    return this.client.thenableCall(
      this.hostname + methodDescriptor.getName(),
      request,
      metadata || {},
      methodDescriptor,
    )
  }

  listSatsangis(
    request: Empty,
    metadata?: grpcWeb.Metadata,
  ): Promise<SatsangiList> {
    const methodDescriptor = new grpcWeb.MethodDescriptor<Empty, SatsangiList>(
      `/${SERVICE_NAME}/ListSatsangis`,
      grpcWeb.MethodType.UNARY,
      Empty,
      SatsangiList,
      (req: Empty) => req.serializeBinary(),
      SatsangiList.deserializeBinary,
    )

    return this.client.thenableCall(
      this.hostname + methodDescriptor.getName(),
      request,
      metadata || {},
      methodDescriptor,
    )
  }
}
