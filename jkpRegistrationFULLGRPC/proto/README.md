# proto/

**Single source of truth for all API types.** One `./generate` → both Python + TypeScript.

> **POC Stage Note:** This structure (proto files at root as the single source of truth) is the **industry standard** for gRPC projects. As we move from POC into actual production, versioning and directory structure will be refined based on project needs (e.g., `proto/v1/`, `proto/v2/` for API versioning, or monorepo patterns).

```
.proto files ──→ ./generate ──┬──→ server/app/generated/  (Python)
                              └──→ client/src/generated/  (TypeScript)
```

## Files

```
proto/
├── *.proto        ← define messages + services here
├── buf.yaml       ← buf module config
├── buf.gen.yaml   ← TypeScript codegen (buf remote plugin)
└── generate       ← run this (handles both languages)
```

## Usage

```bash
./proto/generate
```

## Prerequisites

| Tool | Install (macOS/Linux) | Install (Windows) |
|------|----------------------|-------------------|
| **buf** | `brew install bufbuild/buf/buf` | `scoop install buf` |
| **uv** | `curl -LsSf https://astral.sh/uv/install.sh \| sh` | `powershell -c "irm https://astral.sh/uv/install.ps1 \| iex"` |
| **bun** | `curl -fsSL https://bun.sh/install \| bash` | `powershell -c "irm bun.sh/install.ps1 \| iex"` |

Python deps (auto-installed by `uv sync` in `server/`):
- `grpcio-tools` — generates `_pb2.py`, `_pb2_grpc.py`, `_pb2.pyi`
- `protobuf` — runtime for generated code

TypeScript deps (auto-installed by `bun install` in `client/`):
- `@bufbuild/protobuf` — runtime for generated code

## How it works

```
                    ┌─────────────────────────────────┐
                    │         proto/*.proto            │
                    │   (messages + services)          │
                    └──────────┬──────────────────────-┘
                               │
                         ./generate
                               │
              ┌────────────────┼────────────────┐
              │                                 │
     grpcio-tools (local)              buf remote plugin
              │                                 │
   ┌──────────────────────┐        ┌────────────────────┐
   │  server/app/generated│        │client/src/generated │
   │  ├── *_pb2.py        │        │  └── *_pb.ts        │
   │  ├── *_pb2_grpc.py   │        └────────────────────┘
   │  └── *_pb2.pyi       │
   └──────────────────────┘
```

> Python uses `grpcio-tools` (not buf remote) to guarantee protobuf version compatibility.
