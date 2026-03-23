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

**The Architecture Choice:**\
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

## 10. File Storage (Photos & ID Proofs)

> **TL;DR:** We will use a self-hosted S3-compatible object storage (like MinIO) to store the ID proofs and photos for the 100k-200k Satsangis, rather than polluting the PostgreSQL database with binary blobs.

**The Context & Motivation:**
With 1-2 Lakh (100k-200k) users, storing photos and scanned ID proofs directly inside a PostgreSQL database (`bytea` columns) will massively bloat the database size. This makes backups painfully slow and degrades database performance. Furthermore, gRPC is optimized for structured data, not streaming large binary files.

**The Architecture Choice:**
We will deploy **MinIO** (a lightweight, open-source S3 alternative) via Docker alongside our database.
- **Why it makes sense:** The React frontend will request a secure "Pre-signed URL" from the Python backend via gRPC. The frontend will then upload the photo *directly* to MinIO using standard HTTP. This keeps the heavy file traffic off our gRPC backend entirely.
- **Backup Strategy:** The MinIO data volume will be backed up to the secondary in-house server using tools like `rsync` or `rclone`, running on a similar schedule as the database snapshots.

---

## 11. Database Migrations (Schema & Legacy Data)

> **TL;DR:** We will evaluate specific schema migration tooling (like Alembic) when the need arises, but we will rely on dedicated Python scripts to handle the massive legacy data migration for Phase 1.

**The Context & Motivation:**
As the application evolves, we need a safe way to add/remove columns to the PostgreSQL database without breaking the app for the 50 concurrent staff users. Additionally, we must migrate 1-2 Lakh legacy user records from the old system into this new structured database.

**The Architecture Choice:**
- **Schema Evolution:** We are deferring the choice of a specific schema migration framework (like Alembic or Flyway) until the application requires its first structural update post-launch. For now, the schema will be defined via standard initialization scripts.
- **Legacy Data Migration:** We will write a dedicated ETL (Extract, Transform, Load) Python script for the massive 100k+ row data migration. This script will read the old database/CSVs, validate the data using our strict Pydantic models, and bulk-insert it into the new PostgreSQL database before Phase 1 goes live.

---

## 12. CI/CD & Deployment Pipeline

> **TL;DR:** We use a Hybrid Deployment model: GitHub Actions automatically builds the Docker images, but deployment to the VPN server is triggered manually by a developer choosing a specific stable build.

**The Context & Motivation:**
We want to avoid the "works on my machine" problem by ensuring all code is built in a clean, isolated environment. However, we do not want *Continuous Deployment* (where every push to `main` instantly goes live to staff). We need tight control over exactly when updates happen and the ability to test builds on a staging server first.

**The Architecture Choice:**
- **The Build (Automated):** When code is merged to `main`, GitHub Actions automatically compiles the React app, builds the Python backend, and pushes the Docker images to a private registry (like GitHub Container Registry).
- **The Deploy (Manual):** An admin SSHs into the VPN server (Test or Production) and explicitly pulls the specific image tag they want to deploy (e.g., `docker compose pull && docker compose up -d`). This ensures we only roll out features when the organization is ready, preventing unexpected mid-day updates.

---

## 13. Logging & Monitoring (Docker + Sentry)

> **TL;DR:** We use standard Docker logs for basic infrastructure health, and integrate the Sentry SDK into our code to automatically catch, alert, and trace application crashes.

**The Context & Motivation:**
If the app crashes for a user in another geography, the developers need to know exactly *what* broke and *where* without asking the user to read complex error codes.

**The Architecture Choice:**
- **Docker Logs (The Baseline):** Docker naturally captures anything `print()`ed to the console. This is useful for checking if the server actually started, but terrible for debugging deep code issues because logs lack stack traces and user context.
- **Sentry (The Application Monitor):** We will embed the Sentry SDK into both the React frontend and the Python backend. If a user clicks a button and a null-pointer exception occurs, Sentry intercepts it before it crashes the app. It packages the exact line of code that failed, the user's browser details, and the gRPC payload into a neat alert sent to the developer team. It provides intelligent error tracking without the massive overhead of managing a custom Prometheus/Grafana stack.

---

## 14. Server Topology (Single Node vs Split Nodes)

> **TL;DR:** For Phase 1, we will deploy everything (Proxy, Backend, PostgreSQL, MinIO, SuperTokens) on a **Single Powerful Server** using Docker Compose.

**The Context & Motivation:**
With 200k registrations, the database and file storage (MinIO) will consume significant disk space (~400GB+) and memory. The compute layer (Python/gRPC) is CPU-bound. Splitting these into multiple servers (e.g., Server A for Compute, Server B for Database, Server C for MinIO) increases fault tolerance but drastically increases operational complexity and network latency.

**The Architecture Choice:**
We will use a **Single Server Topology** for Phase 1.
- **Why it makes sense:** Docker Compose natively handles networking between the containers instantly. If we split the database to a different physical server, we introduce network latency between the gRPC backend and the database, and we have to manage multiple Linux environments.
- **The Caveat:** Because we are using a single server, the "Automated Scheduled Snapshots" and "MinIO syncs" to a *secondary in-house server* (as defined in our backup strategy) become absolutely critical to protect against a single-machine hardware failure. If the compute load becomes too high in Phase 2, we can easily split the stateless Docker containers (Python/Proxy) to a new server because they are decoupled via Environment Variables.
