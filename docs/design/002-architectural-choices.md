# Architecture Choices & Guidelines

This document serves as a living record of the core deployment and architectural decisions made for the JKP Registration system. It is designed to be read by the team to understand *why* the system is built this way, and how it differs from the initial local development state.

---

## 1. gRPC as the Backend Contract

> **TL;DR:** gRPC enforces strict data types and is much faster than JSON. Keep using the `.proto` files to define the contract.

**The Context & Motivation:**
As systems scale, REST with JSON payloads causes friction. Text parsing is slow, payloads are bloated, and without strict contracts, the frontend and backend often disagree on data types.

**The Architecture Choice:**
We shift the contract to compile-time using a strict Interface Definition Language (`.proto` files). Data is transmitted using highly compressed binary format over HTTP/2. This makes network boundaries feel like strongly-typed local function calls. 
- We use **Protocol Buffers** which allow schema evolution (adding/removing fields) without breaking existing clients.

**Current vs. Proposed State:**
- **Current State:** The code already defines the schema in `satsangi.proto` and the React frontend uses the generated TypeScript client (`SatsangiServiceClientPb`).
- **Proposed State:** Keep this exactly as is. We are already doing this correctly.

---

## 2. Dedicated grpc-web Proxy

> **TL;DR:** Browsers can't speak native gRPC, so they need a translator. We are splitting the translator (proxy) and the business logic (backend) into two separate services for better scaling and debugging.

**The Context & Motivation:**
Browsers fundamentally cannot speak native gRPC because they lack low-level control over HTTP/2 framing. 

**The Architecture Choice:**
We introduce a dedicated translation layer (a proxy) that intercepts standard browser requests, unwraps the payload, forwards a native gRPC call to the backend, and repacks the response for the browser. This keeps the core backend "pure" gRPC and decouples translation from business logic.

**Current vs. Proposed State:**
- **Current State:** You have a custom FastAPI app (`main.py`) running on port `8080` acting as the proxy. *However*, this proxy script currently imports and starts the native gRPC server itself. They run in the same Python process.
- **Proposed State:** Separate them into two independent services (e.g., in a `docker-compose.yml`). The proxy container only does translation; the backend container only does business logic. 

---

## 3. The Edge Web Server (Solving CORS and Hosting the App)

> **TL;DR:** We will put an Edge Web Server (like Caddy/Nginx) in front of everything to kill CORS errors and serve the built React files directly. The heavy Vite dev server will be removed from production.

**The Context & Motivation:**
Hosting frontends and backends on different domains or ports (like `:5174` and `:8080`) triggers the browser's Same-Origin Policy (SOP). This forces complex CORS preflight requests and complicates security. Also, treating the frontend as a completely separate entity from the backend can introduce version drift (the UI expects v2 of the API, but the backend is still on v1).

**The Architecture Choice:**
The browser trusts the origin exactly. By placing a reverse proxy (an "Edge Web Server") at the very front of the system, we solve both problems:
1. It routes traffic based on URL paths (`/grpc/` to proxy, `/` to frontend), making the browser perceive a single, unified origin. This instantly eliminates CORS issues.
2. It serves the pre-built static React application directly, guaranteeing version synchronization with the backend APIs it protects. Deployments become atomic.

**Current vs. Proposed State:**
- **Current State:** The frontend runs on `http://localhost:5174` (via a heavy Vite dev server), the proxy runs on `http://localhost:8080`, and the backend is on `localhost:50051`. Because they are on different ports, you had to add a very permissive CORS policy (`allow_origins=["*"]`).
- **Proposed State:** You will run `bun run build` to generate plain, static HTML/JS/CSS files. You will put an Edge Web Server on port 443 (HTTPS) to serve these files and route backend traffic. The Node development server is removed.

---

## 4. Self-Hosted PostgreSQL (with Cloud-Ready Path)

> **TL;DR:** We self-host the database for data privacy, but we inject the connection string via Environment Variables so we can move to AWS/Cloud later without changing any Python code.

**The Context & Motivation:**
Data sensitivity mandates strict local custody (self-hosting). However, hardcoding local infrastructure details creates a brittle system that cannot easily migrate to a managed public cloud later when security postures or scale requires it.

**The Architecture Choice:**
Treat the database purely as an attached resource accessible via a standardized URI. The application code must remain entirely ignorant of *where* the database lives, relying solely on environment injection (Environment Variables) to locate its state. The database will bind only to a private internal network interface for security.

**Current vs. Proposed State:**
- **Current State:** The codebase currently assumes the database is running locally and likely has connection details hardcoded or loosely managed for local dev.
- **Proposed State:** The application must read the connection string from an environment variable (e.g., `DATABASE_URL`). You will run a dedicated PostgreSQL instance on a secure, private network, and inject that specific URL into the backend container.
