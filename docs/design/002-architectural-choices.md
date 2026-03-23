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

## 5. Self-Hosted PostgreSQL (with Cloud-Ready Path)

> **TL;DR:** We self-host the database for data privacy, but we inject the connection string via Environment Variables so we can move to AWS/Cloud later without changing any Python code.

**The Context & Motivation:**
Data sensitivity mandates strict local custody (self-hosting). However, hardcoding local infrastructure details creates a brittle system that cannot easily migrate to a managed public cloud later when security postures or scale requires it.

**The Architecture Choice:**
Treat the database purely as an attached resource accessible via a standardized URI. The application code must remain entirely ignorant of *where* the database lives, relying solely on environment injection (Environment Variables) to locate its state. The database will bind only to a private internal network interface for security.

**Current vs. Proposed State:**
- **Current State:** The codebase currently assumes the database is running locally and likely has connection details hardcoded or loosely managed for local dev.
- **Proposed State:** The application must read the connection string from an environment variable (e.g., `DATABASE_URL`). You will run a dedicated PostgreSQL instance on a secure, private network, and inject that specific URL into the backend container.

---

## 6. Authentication (Self-Hosted Identity Provider)

> **TL;DR:** To securely authenticate the 100-200 staff members without writing a custom, potentially insecure login system, we will deploy a self-hosted open-source identity provider (like SuperTokens or Logto) strictly for this application in Phase 1.

**The Context & Motivation:**
Building custom authentication (password hashing, session cookies, password resets) from scratch is a significant security risk and time sink. We need a secure way to manage our 100-200 users. While we eventually want a centralized SSO for all company apps, we are scoping this strictly to this application for Phase 1.

**The Architecture Choice:**
We will deploy **SuperTokens** (or Logto) in a Docker container alongside our application.
- **Why it makes sense:** It keeps all user data strictly within our internal network, avoids public cloud dependencies, and removes the burden of maintaining custom login code. When the organization is ready, this instance can be scaled into a centralized Identity Provider.
- **Future Public Registration:** For Phase 2 (public self-registration), we plan to use a Firebase OTP mechanism. This allows end-users to verify their identity via SMS without needing a persistent account or password, while avoiding hard dependencies on Cloudflare.

---

## 7. Database Backup & Recovery Strategy

> **TL;DR:** We utilize automated interval backups to a secondary in-house server, with continuous Write-Ahead Log (WAL) archiving as a secondary "nice-to-have" goal.

**The Context & Motivation:**
We need a reliable recovery strategy that protects the data entered by 50-60 concurrent staff members. We are currently self-hosting but want to ensure we don't lose days of work if a primary server fails.

**The Architecture Choice:**
We are taking a phased maturity approach to database backups:

1. **Current Strategy (Phase 1): In-House Automated Backups**
   - **Primary Goal:** Automated scheduled snapshots (e.g., `pg_dump` every few hours) securely copied to a physically separate in-house server.
   - **Secondary Goal (Nice-to-Have):** Streaming continuous Write-Ahead Logs (WAL) to the secondary server to achieve Point-in-Time Recovery (PITR) and reduce potential data loss to near-zero.
   - *Pros:* Zero ongoing cloud costs and protects against single-machine failure.

2. **Better Alternatives (Future Enhancements):**
   - **Off-Site Cloud Backup:** Sending the backups to a secure cloud bucket (like AWS S3) instead of a local server to protect against site-wide disasters.
   - **Managed Cloud Database (e.g., AWS RDS):** Moving the database to a cloud provider that automatically handles hardware maintenance, OS patching, and instantaneous backups. Because the application reads the database location from an environment variable (`DATABASE_URL`), this migration will require zero code changes.

---

## 8. Network Security (Site-to-Site VPN)

> **TL;DR:** We secure the application using a Site-to-Site VPN rather than exposing it to the public internet or relying on individual Zero-Trust clients.

**The Context & Motivation:**
The system must be securely accessed by 100-200 staff members across 4-5 physical office locations. We considered three models:
1. **Public Internet with WAF:** Buying a public domain and relying entirely on a Web Application Firewall (like Cloudflare) and login screens. *Risk:* The server is constantly exposed to global bots and zero-day scanners.
2. **Zero Trust Network Access (e.g., Tailscale):** Every staff member installs a software client on their device. *Risk:* High operational overhead troubleshooting 200 software installations.
3. **Site-to-Site VPN:** Connecting the routers of the 5 offices directly over encrypted tunnels.

**The Architecture Choice:**
We mandate a **Site-to-Site VPN**. 
- **Why it makes sense:** It provides network-level invisibility. To the outside world, the application literally does not exist. Staff members do not need to install any custom VPN software on their devices; they simply connect to the office Wi-Fi, and the router handles the secure routing to the internal server. It maximizes security with zero end-user friction.

---

## 9. Cloud Readiness (Twelve-Factor App)

> **TL;DR:** Although the system is designed to be self-hosted on an internal network, its architecture is "Cloud-Native", meaning it can be migrated to AWS/GCP tomorrow with zero code changes.

**The Context & Motivation:**
Many self-hosted applications become brittle over time because developers hardcode local file paths, assume local database presence, or rely on state stored directly on the server's hard drive. This makes future cloud migration painful.

**The Architecture Choice:**
We enforce strict **Twelve-Factor App** principles to ensure true cloud readiness:
1. **Containerization:** Every single component (UI, Proxy, Backend, Database) is isolated in its own Docker container. Cloud providers are built natively to run containers.
2. **Stateless Compute:** The Python backend and FastAPI proxy do not store session data or files on their local drives. If the server is destroyed and restarted elsewhere, no data is lost.
3. **Environment Parity:** The database connection (`DATABASE_URL`), auth secrets, and proxy endpoints are entirely decoupled from the code and injected via Environment Variables. Moving from a local server to AWS simply requires updating a `.env` file, with zero lines of Python or React code changed.
