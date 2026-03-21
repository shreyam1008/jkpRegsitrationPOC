/**
 * gRPC-web service client for DevoteeService — MINIMAL version.
 *
 * Just ONE method: listDevotees.
 *
 * How it works:
 *   1. Browser creates an Empty protobuf message
 *   2. grpc-web library serializes it to binary
 *   3. Wraps in grpc-web frame (5-byte header + base64)
 *   4. POSTs to proxy at :8080
 *   5. Proxy forwards to gRPC server at :50051
 *   6. Response comes back the same way in reverse
 */

import * as grpcWeb from 'grpc-web'
import { DevoteeList, Empty } from './devotee_pb'

const SERVICE_NAME = 'jkp.demo.v1.DevoteeService'

export class DevoteeServiceClient {
  private client: grpcWeb.AbstractClientBase
  private hostname: string

  constructor(hostname: string) {
    this.hostname = hostname
    this.client = new grpcWeb.GrpcWebClientBase({})
  }

  listDevotees(request: Empty): Promise<DevoteeList> {
    const methodDescriptor = new grpcWeb.MethodDescriptor<Empty, DevoteeList>(
      `/${SERVICE_NAME}/ListDevotees`,
      grpcWeb.MethodType.UNARY,
      Empty,
      DevoteeList,
      (req: Empty) => req.serializeBinary(),
      DevoteeList.deserializeBinary,
    )

    return this.client.thenableCall(
      this.hostname + methodDescriptor.getName(),
      request,
      {},
      methodDescriptor,
    )
  }
}
