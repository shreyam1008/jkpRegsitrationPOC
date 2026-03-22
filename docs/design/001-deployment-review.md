# Deployment Review for gRPC Registration App

This plan reviews the current gRPC deployment approach against the target production shape using self-hosted PostgreSQL, a dedicated grpc-web proxy, single-domain HTTPS, and same-domain React hosting.

## Scope
- Compare the current setup with the recommended production topology
- Identify benefits of the target design for this internal registration system
- Highlight major disadvantages or risks in the current implementation
- Keep the design cloud-ready for a later public-cloud move

## Current-State Findings to Validate
- The browser uses `grpc-web` and currently targets `http://localhost:8080`
- The proxy is implemented in FastAPI and currently starts the native gRPC server in-process
- The native gRPC server listens on `:50051`
- The proxy currently uses `grpc.insecure_channel("localhost:50051")`
- CORS is currently open with `allow_origins=["*"]`
- Local/dev flow uses separate frontend, proxy, and gRPC processes

## Review Focus
1. Explain why the target topology is better than the current dev-style setup
2. Assess whether self-hosted PostgreSQL is reasonable now for sensitive data
3. Define the intended production request flow under one HTTPS domain
4. Identify major disadvantages in the current setup that should be addressed before production
5. Note what to preserve so migration to public cloud later stays easy

## Expected Recommendations
- Keep gRPC as the backend contract
- Keep a grpc-web bridge for browser access
- Separate concerns between frontend hosting, grpc-web proxy, gRPC service, and database
- Expose only HTTPS publicly; keep database and native gRPC private
- Externalize config for proxy target, frontend base URL, and database connection
- Tighten CORS, transport security, and operational controls for production

## Key Risk Areas to Evaluate
- In-process coupling of proxy and gRPC server
- Hardcoded localhost URLs and ports
- Lack of production-grade TLS between components
- Broad CORS policy
- No explicit secret/config strategy shown yet
- Unknown backup, restore, and monitoring posture for self-hosted PostgreSQL

## Output for Review
- Concise architecture assessment
- Benefits of the target design over the current setup
- Major disadvantages to fix first
- Short list of next architectural decisions
