# Architecture Choices & Guidelines

This document serves as a living record of the core deployment and architectural decisions made for the JKP Registration system. It is designed to be read by the team to understand *why* the system is built this way, and how it differs from the initial local development state.

---

## 1. Web Application over Desktop Client

> **TL;DR:** A responsive Web App ensures zero-installation rollouts, instant global updates, immediate security patching, and paves the way for future public self-registration.

**The Context & Motivation:**
Initially, staff might use PCs to register members, which could suggest a native desktop app. However, a desktop app requires manual installation, OS-specific updates, and restricts staff to specific machines across our 4-5 geographies. Furthermore, the roadmap includes two critical future requirements:
1. **Mobile Access:** Staff need read/write access via mobile devices while on the floor.
2. **Future Self-Registration:** Eventually, users will register themselves from their own devices.

**The Architecture Choice:**
We build a responsive Web Application (React). 
- **Why it's better:** Updates are instant and global—there is no local troubleshooting involved. If a security vulnerability is found, patching the web app instantly protects all users. It guarantees that any device with a browser can access the system. We mandate a mobile-friendly UI design from day one to support staff and prepare the exact same UI components for future public self-registration.

---

## 2. gRPC as the Backend Contract

> **TL;DR:** gRPC enforces strict data types and is much faster than JSON. Keep using the `.proto` files to define the contract. It provides 2.4x smaller payloads and 10x faster serialization than REST, and AI tooling makes debugging binary payloads easier than reading JSON.

**The Context & Motivation:**
As systems scale, REST with JSON payloads causes friction. Text parsing is slow, payloads are bloated (repeating string keys like `"first_name"` in every payload), and without strict contracts, the frontend and backend often disagree on data types.

**The Architecture Choice:**
We shift the contract to compile-time using a strict Interface Definition Language (`.proto` files). Data is transmitted using a highly compressed binary format over HTTP/2. This makes network boundaries feel like strongly-typed local function calls. 
- We use **Protocol Buffers** which allow schema evolution (adding/removing fields via numbered tags) without breaking existing clients.
- **Why it's better:** Benchmarks show it is ~10x faster and payloads are ~2.5x smaller than JSON. While binary is traditionally hard to read, modern AI tools can instantly decode and diagnose protobuf payloads, making debugging actually *better* than REST.

**Current vs. Proposed State:**
- **Current State:** The code already defines the schema in `satsangi.proto` and the React frontend uses the generated TypeScript client (`SatsangiServiceClientPb`).
- **Proposed State:** Keep this exactly as is. We are already doing this correctly.

---

## 3. Dedicated grpc-web Proxy

> **TL;DR:** Browsers can't speak native gRPC, so they need a translator. We are splitting the translator (proxy) and the business logic (backend) into two separate services for better scaling and debugging.

**The Context & Motivation:**
Browsers fundamentally cannot speak native gRPC because they lack low-level control over HTTP/2 framing. 

**The Architecture Choice:**
We introduce a dedicated translation layer (a proxy) that intercepts standard browser requests, unwraps the payload, forwards a native gRPC call to the backend, and repacks the response for the browser. This keeps the core backend "pure" gRPC and decouples translation from business logic.

**Current vs. Proposed State:**
- **Current State:** You have a custom FastAPI app (`main.py`) running on port `8080` acting as the proxy. *However*, this proxy script currently imports and starts the native gRPC server itself. They run in the same Python process.
- **Proposed State:** Separate them into two independent services (e.g., in a `docker-compose.yml`). The proxy container only does translation; the backend container only does business logic. 

---

## 4. The Edge Web Server (Solving CORS and Hosting the App)

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

## 5. Cloudflare Integration (Public Readiness & WAF)

> **TL;DR:** We integrate Cloudflare primarily to support future public self-registration by providing a massive shield (Web Application Firewall) against bots and malicious traffic, while keeping our internal server secure. In Phase 1, it provides simple Email OTP for our 20 users.

**The Context & Motivation:**
While Phase 1 only serves ~20 internal staff, Phase 2 will introduce public self-registration. Opening a self-hosted server directly to the public internet invites DDoS attacks and vulnerability scanning. Furthermore, for Phase 1, we need a secure way to authenticate the 20 known users without building complex password management systems into the application itself.

**The Architecture Choice:**
We place the application behind **Cloudflare**.
- **The Primary Benefit (WAF):** Cloudflare acts as a Web Application Firewall (WAF) and DDoS shield. When public registration launches, Cloudflare absorbs malicious traffic, ensuring the self-hosted server only handles legitimate requests.
- **Phase 1 Authentication (Zero Trust):** We use Cloudflare Tunnels to connect our server to the internet invisibly, meaning we do not have to open any inbound ports on our office routers. We configure Cloudflare to use Email OTP (One-Time Password) restricted to a hardcoded list of the 20 allowed staff emails. This requires zero code and saves massive development time.
- **Phase 2 Authentication (Centralized SSO):** In the future, we can transition away from Cloudflare OTP to a centralized organization-wide SSO/Identity Provider to ensure login consistency across all company apps.

---

## 6. Database Backup & Recovery Strategy

> **TL;DR:** We are starting with simple interval snapshots stored on a secondary in-house server, with clear upgrade paths to Cloud storage or Managed Databases as the system scales.

**The Context & Motivation:**
We need a reliable recovery strategy that protects the data entered by the 5-7 concurrent staff members without requiring a full-time database administrator. We are currently self-hosting but want to be cloud-ready.

**The Architecture Choice:**
We are taking a phased maturity approach to database backups:

1. **Current Strategy (Phase 1): In-House Server Redundancy**
   - An automated interval script (e.g., `pg_dump` every 3 hours) takes a snapshot of the database and copies it to a physically separate server within the same office network.
   - *Pros:* Easy to configure, zero ongoing cloud costs.
   - *Cons:* Vulnerable to site-wide disasters (fire, power surge) and potential data loss of up to 3 hours.

2. **Better Alternatives (Future Enhancements):**
   - **Off-Site Cloud Backup:** Sending the 3-hour dumps to a secure cloud bucket (like AWS S3) instead of a local server to protect against site-wide disasters.
   - **Continuous WAL Archiving:** Streaming Write-Ahead Logs to achieve Point-in-Time Recovery (PITR), reducing potential data loss from 3 hours to 0 minutes.
   - **Managed Cloud Database (e.g., AWS RDS):** Moving the database to a cloud provider that automatically handles hardware maintenance, OS patching, and instantaneous backups. Because the application reads the database location from an environment variable (`DATABASE_URL`), this migration will require zero code changes.
