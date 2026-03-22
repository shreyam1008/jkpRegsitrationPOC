# Architecture Choices: The Inventor's Perspective (with Current vs Proposed Comparisons)

This document explains the core deployment and architectural decisions made for the JKP Registration system, applying the "Inventor Mental Model" to expose the underlying architectural "why" behind each choice. It also explicitly compares the *Current State* (what is currently in the codebase) with the *Proposed State* (the target production deployment).

---

## 1. gRPC as the Backend Contract

**1. Core Motivation**
As distributed systems scale, REST over HTTP/1.1 with JSON payloads introduces severe friction: text parsing is CPU-intensive, payloads are bloated with repeated keys, and most critically, lack of strict contract enforcement leads to runtime type mismatches between client and server.

**2. Key Insight**
Shift the contract to compile-time using a strict Interface Definition Language (IDL), and transmit data using a highly compressed binary format over multiplexed HTTP/2. The "aha" moment is realizing that the network boundary should feel exactly like calling a strongly-typed local function.

**3. Refinements & Extensions**
- **Protocol Buffers:** Evolved from the need for forward/backward compatibility. Field numbering allows schema evolution without breaking existing clients.
- **Multiplexing & Streaming:** HTTP/2 allows multiple concurrent calls over a single TCP connection, eliminating head-of-line blocking and enabling native streaming without WebSockets.

**4. The Mental Anchor**
gRPC is simply **compile-time type safety stretched across a network boundary**.

**5. Current vs. Proposed State**
- **Current State:** The code already defines the schema in `satsangi.proto` and the React frontend uses the generated TypeScript client (`SatsangiServiceClientPb`).
- **Proposed State:** Keep this exactly as is. You are already doing this correctly.

---

## 2. Dedicated grpc-web Proxy

**1. Core Motivation**
Browsers fundamentally cannot speak native gRPC. They lack low-level control over HTTP/2 framing and cannot read trailing headers (trailers) which gRPC relies on for status codes.

**2. Key Insight**
Introduce a dedicated translation layer (a proxy) that intercepts standard HTTP/1.1 (or HTTP/2) browser requests, unwraps the payload, forwards a native gRPC call to the backend, and repacks the response (and trailers) into a format the browser can digest.

**3. Refinements & Extensions**
- **Decoupling Business Logic:** Moving this translation out of the application code keeps the core backend "pure" gRPC.

**4. The Mental Anchor**
The proxy is an **impedance matcher**. It translates the restrictive vocabulary of browser networking into the unrestricted binary streams required by backend microservices.

**5. Current vs. Proposed State**
- **Current State:** You have a custom FastAPI app (`jkpRegistrationFULLGRPC/server/app/main.py`) running on port `8080` acting as the proxy. *However*, this proxy script currently imports and starts the native gRPC server itself (`start_grpc_server(port=50051)`). They run in the same Python process.
- **Proposed State:** Separate them into two independent services (e.g., in a `docker-compose.yml`). The proxy container only does translation; the backend container only does business logic. This separation is standard for production because it allows scaling and restarting them independently.

---

## 3. Single Domain Over HTTPS

**1. Core Motivation**
Hosting frontends on `app.domain.com` and backends on `api.domain.com` (or separate ports like `:5174` and `:8080`) triggers the browser's Same-Origin Policy (SOP). This forces complex CORS preflight requests (`OPTIONS`) and complicates security.

**2. Key Insight**
The browser trusts the origin exactly. By placing a reverse proxy at the edge that routes traffic based on URL paths (rather than subdomains or ports), the browser perceives a single, unified origin.

**3. Refinements & Extensions**
- **Path-Based Routing:** `/api/*` or `/grpc/*` flows to the backend proxy, everything else to the static frontend.

**4. The Mental Anchor**
**Consolidate at the edge to deceive the browser.** By masking distributed microservices behind a single URL, you bypass browser security friction.

**5. Current vs. Proposed State**
- **Current State:** The frontend runs on `http://localhost:5174`, the proxy runs on `http://localhost:8080`, and the backend is on `localhost:50051`. Because the frontend (`5174`) calls a different port (`8080`), you had to add a very permissive CORS policy (`allow_origins=["*"]`) in `main.py` just to make it work locally.
- **Proposed State:** Put a web server (like Caddy or Nginx) in front on port 443 (HTTPS). Staff visit `https://registration.yourorg.org`. The web server routes `/` to the React app and `/grpc/` to the proxy. Because it's all one domain, you don't need wild CORS policies anymore.

---

## 4. Same-Domain React App Hosting

**1. Core Motivation**
For internal applications, treating the frontend as a highly distributed, CDN-hosted artifact separate from backend deployments introduces version drift (the UI expects v2 of the API, but the backend is still on v1).

**2. Key Insight**
For moderate-scale internal tools, the frontend is just another static asset of the deployment. Serve the pre-built React application from the same physical infrastructure and edge gateway as the backend to guarantee version synchronization.

**3. Refinements & Extensions**
- **Atomic Deployments:** UI and API are deployed together.

**4. The Mental Anchor**
**Deployment atomicity over geographic distribution.** Guaranteeing that the UI perfectly matches the API version is vastly more important than global CDN delivery times for an internal tool.

**5. Current vs. Proposed State**
- **Current State:** You are running the React app using the Vite development server (`bun run dev`, which spins up a live-reloading Node server on `5174`).
- **Proposed State:** You will run `bun run build` to generate plain, static HTML/JS/CSS files. The edge web server (Caddy/Nginx) will serve these static files directly. The Node/Bun development server is entirely removed from the production environment.

---

## 5. Self-Hosted PostgreSQL (with Cloud-Ready Path)

**1. Core Motivation**
Data sensitivity mandates strict local custody (self-hosting), but hardcoding local infrastructure (e.g., `localhost:5432`) creates a brittle system that cannot easily migrate to a managed public cloud later.

**2. Key Insight**
Treat the database purely as an attached resource accessible via a standardized URI. The application code must remain entirely ignorant of *where* the database lives, relying solely on environment injection to locate its state.

**3. Refinements & Extensions**
- **Network Isolation:** The database binds only to a private internal network interface.

**4. The Mental Anchor**
**State is a strictly injected dependency.**

**5. Current vs. Proposed State**
- **Current State:** The codebase currently assumes the database is running locally and likely has connection details hardcoded or loosely managed for local dev.
- **Proposed State:** The application must read the connection string from an environment variable (e.g., `DATABASE_URL`). In your self-hosted production environment, you will run a dedicated PostgreSQL instance on a secure, private network, and inject that specific URL into the backend container. When you eventually move to the cloud, you simply change the environment variable to point to AWS RDS/Azure without touching the Python code.
