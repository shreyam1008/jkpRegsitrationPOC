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

## 6. Authentication (Centralized SSO via Keycloak)

> **TL;DR:** To securely authenticate the 100-200 staff members and establish a foundation for all future organization applications, we will deploy **Keycloak** as our self-hosted Identity Provider.

**The Context & Motivation:**
Building custom authentication (password hashing, session cookies, password resets) from scratch is a significant security risk and time sink. We need a secure, self-hosted way to manage our 100-200 users. Because the organization plans to roll out more internal applications in the future, we need an Identity Provider capable of acting as a true Single Sign-On (SSO) hub.

**The Architecture Choice:**
We will deploy **Keycloak** (maintained by Red Hat) in a Docker container alongside our application.

We evaluated several alternatives before selecting Keycloak:
- *SuperTokens:* Excellent developer framework, but primarily designed to secure a single app. Building a centralized SSO hub for other apps requires too much custom code.
- *Logto / Zitadel:* Excellent modern IdPs, but many of their advanced multi-tenant and enterprise SSO features are locked behind paid tiers or enterprise licenses.

**Why Keycloak wins for us:**
1. **100% Free & Open Source:** There are no paid enterprise tiers, no user limits, and no paywalls for advanced features (like SAML or identity brokering).
2. **Industry Standard SSO:** It natively supports standard OIDC (OpenID Connect) and SAML protocols. When the organization builds a second app next year, it can connect to this Keycloak instance with zero additional licensing costs.
3. **No-Code Management:** The entire user directory, password reset flows, and application clients are managed visually through the Keycloak Admin Console.

- **Future Public Registration:** For Phase 2 (public self-registration), we plan to use a Firebase OTP mechanism. This allows end-users to verify their identity via SMS without needing a persistent account or password in Keycloak.

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

## 10. File Storage (MinIO vs Local Hard Disk)

> **TL;DR:** We will use **MinIO** (a self-hosted S3-compatible object storage) to manage media files (Photos, ID Proofs, Form C docs) instead of raw local disk folders or database blobs, keeping total storage strictly under 200GB.

**The Context & Motivation:**
With scaling expectations up to 500,000 registrations, we must efficiently manage media data. This includes standard registrations and specialized Form C documents for foreign nationals. We are implementing hard caps to ensure total media storage does not exceed 200GB.

We considered two local-storage approaches:
1. **Raw Local Hard Disk (Docker Volumes):** The Python API receives the files via gRPC (or REST) and saves them to a folder like `/var/app/data/photos/`. 
   - *Problem:* Passing binary files through the gRPC translation proxy adds massive overhead to the Python server. Additionally, creating raw network copies of hundreds of thousands of individual tiny files using `rsync` for backups takes hours and causes disk I/O bottlenecks.
2. **MinIO Object Storage:** A dedicated container running on the local server that manages files like an enterprise database instead of a raw folder.

**The Architecture Choice:**
We will deploy **MinIO**.
- **Why it makes sense (Direct Uploads):** The React frontend will request a secure "Pre-signed URL" from the Python backend via gRPC. The frontend will then upload the photo *directly* to the MinIO container using standard HTTP. This completely bypasses the Python backend, keeping the compute server extremely fast.
- **Why it makes sense (Backups):** MinIO has built-in features to continuously "mirror" its contents to a secondary backup server instantly, preventing the need to write fragile custom `rsync` scripts.

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

## 14. Server Topology (Split Node Architecture)

> **TL;DR:** For Phase 1 Production, we will deploy a **Split Node Architecture** using two separate physical servers: a stateless Compute Server and a stateful Storage Server. We will also maintain a dedicated **Single-Machine Staging Server**.

**The Context & Motivation:**
With the scale reaching up to 500,000 entries (1TB+ of media), placing everything on a single machine risks resource starvation (e.g., heavy database indexing slowing down the Python proxy). We also need a safe way to test updates before pushing to production without interfering with active staff members.

**The Architecture Choice (Production):**
We will use a **Two-Server Topology** for the live environment.
- **Server A (Compute Node):** Runs the Edge Proxy, gRPC Proxy, Python Backend, and SuperTokens. It is 100% stateless. If it crashes, we can spin up a new server and pull the Docker images instantly with zero data loss.
- **Server B (Storage Node):** Runs PostgreSQL and MinIO. This server focuses entirely on high-speed disk I/O and strict backup routines. 
- **Why it makes sense:** It physically isolates CPU-bound tasks from I/O-bound tasks. It significantly increases security, as Server B can be placed on a strict private subnet that physically cannot talk to the public internet.

**The Architecture Choice (Staging/Test Server):**
We will maintain a **Dedicated Staging Server** (a smaller, single remote server) running alongside production on the VPN. 
- **Purpose:** All Docker images built by GitHub Actions will be manually pulled and deployed to this staging server first. It allows developers and project leads to click through the new UI and verify migrations *before* touching the Split Node production servers.
- **Topology & Backups:** This staging environment will run the entire stack (Compute + Database + MinIO) on a single machine via a unified `docker-compose-staging.yml` file to save costs. **The staging server will explicitly NOT be backed up**, as it only holds synthetic/temporary test data.

---

## 15. Search & Indexing Strategy

> **TL;DR:** We will rely on native PostgreSQL extensions (`pg_trgm` and Full-Text Search) to handle searching across 500,000 records, deferring dedicated search engines (like Elasticsearch or Typesense) to avoid unnecessary infrastructure bloat.

**The Context & Motivation:**
With scaling expectations up to 500,000 (5 Lakh) registrations, staff members will frequently need to search for existing Satsangis to avoid duplicate entries. Standard SQL `LIKE '%name%'` queries require scanning every single row in the database, which becomes painfully slow (taking seconds rather than milliseconds) at this scale.

**The Architecture Choice:**
We will use **PostgreSQL Trigram Indexes (`pg_trgm`)** and **Native Full-Text Search**.
- **Why it makes sense:** PostgreSQL is incredibly powerful. By adding a simple extension like `pg_trgm`, we can enable lightning-fast "fuzzy matching" (e.g., finding "Shreyam" even if the staff typed "Shryam") without needing to deploy, sync, and manage a completely separate search container.
- **When to reconsider:** If we ever implement complex, multi-faceted filtering (e.g., "Find all users in Delhi who registered between 2018-2020 and have a Form C, sorted by relevance"), we will re-evaluate moving search to a dedicated engine in Phase 2.

---

## 16. Background Job Processing

> **TL;DR:** We will use a dedicated **Background Task Queue** (like Celery + Redis or native Python async workers) to handle long-running tasks, ensuring the gRPC API remains instantly responsive.

**The Context & Motivation:**
Certain tasks take too long to run synchronously within an HTTP/gRPC request. For example:
1. Exporting 50,000 user records to a CSV file for reporting.
2. The initial one-time ETL migration of 200,000 legacy records.
3. Sending out bulk SMS OTPs or notifications.
If the Python gRPC server tries to do this while the user's browser waits, the connection will time out, and the server will be blocked from handling other staff members.

**The Architecture Choice:**
We will implement a **Background Task Queue** in the Compute Node.
- **Why it makes sense:** When a staff member clicks "Export Data", the Python backend instantly replies "Job Started" and returns a Task ID. A separate Python worker process (running in the background) picks up the heavy work, generates the CSV, and saves it to MinIO. The React UI can simply poll the server to see when the file is ready to download. This keeps the main application completely unblocked.
