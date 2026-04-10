# .NET Architectural Choices

This document records the architectural decisions made as part of the backend migration to .NET Core (ASP.NET Core). It covers why the switch was made, what .NET provides natively that previously required external tooling, and the evaluation of key infrastructure components (API strategy, object storage, authentication, queuing).

> The original Python-era decisions are preserved in `002-architectural-choices.md` and `003-web-hosting-concepts.md` for historical reference. This document supersedes those for all forward-looking architectural guidance.

---

## 1. Why .NET Core / C#

> **TL;DR:** .NET gives us compile-time type safety, a REST API with an easy upgrade path to gRPC for performance-critical endpoints, true multi-threading, and a rich built-in ecosystem for auth, caching, and background tasks — reducing our infrastructure and third-party dependency count significantly.

**The Motivation:**

The decision to use .NET Core / C# for the backend was driven by three key factors:

1. **Team Know-How:** Team members who worked on the previous version of the application have existing C#/.NET experience and, critically, carry institutional knowledge of the business logic. Using .NET allows them to contribute immediately without a language learning curve, and to translate domain knowledge directly into code without a re-learning overhead.

2. **Built-in Ecosystem:** .NET provides natively what other stacks require third-party libraries or additional infrastructure for — gRPC-web middleware, authentication, background task processing, dependency injection, caching, and ORM. This reduces the number of moving parts and external dependencies to maintain.

3. **Compile-Time Safety:** C#'s type system catches entire classes of bugs at build time. For a multi-year internal system with evolving requirements and potential developer turnover, the compiler acts as a safety net that ensures refactoring confidence.

**What .NET Provides Natively:**

| Capability | .NET Stack |
|---|---|
| Type safety | Enforced at compile time (nullable reference types, strong generics) |
| REST API | ASP.NET Core Minimal APIs / Controllers with JSON serialization |
| gRPC (optional) | `grpc-dotnet` built into ASP.NET Core — available for perf-critical endpoints |
| Multi-threading | True multi-threading across CPU cores |
| Background tasks | Built-in `BackgroundService` + `Channel<T>` |
| Auth middleware | Built-in `AddAuthentication().AddJwtBearer()` + ASP.NET Identity |
| In-memory caching | `IMemoryCache` (with expiration, size limits, thread-safe) |
| ORM | Entity Framework Core (async-first, code-first migrations) |
| Dependency injection | Built-in DI container |

**AI/ML Note:** Python remains the superior choice for AI/ML workloads (facial recognition, chatbot, embeddings). If these Phase 2 features require heavy ML processing, a lightweight Python microservice can be introduced as a sidecar — called via REST or gRPC from the .NET backend. The .NET backend remains the single source of truth for business logic and data access.

---

## 2. API Strategy: REST-First with gRPC Upgrade Path

> **TL;DR:** We use REST (JSON over HTTP) as the primary API for simplicity and debuggability. ASP.NET Core makes it trivial to add gRPC endpoints alongside REST for specific performance-critical use cases later, without any architectural changes.

### Why REST-First

**Debugging & Developer Experience:**
REST with JSON is human-readable. Every request and response can be inspected in the browser's Network tab, tested with `curl`, and logged as plain text. For a team ramping up on a new codebase, this transparency dramatically reduces debugging time compared to binary gRPC payloads that require specialized tooling to decode.

**Ecosystem Compatibility:**
REST is universally supported. TanStack Query on the frontend works natively with REST. Third-party integrations, webhooks, and future public APIs all speak REST. There is no grpc-web translation layer needed — the browser talks directly to the API.

**Simplicity:**
No `.proto` files to maintain, no code generation step, no Protobuf serialization/deserialization layer. The API contract is defined by C# DTOs (Data Transfer Objects) and Swagger/OpenAPI documentation is auto-generated.

### When to Add gRPC

gRPC becomes valuable when:
- **Bulk data transfer** — e.g., syncing 50,000 records to another service. Protobuf payloads are ~2.5x smaller than JSON.
- **Server-to-server communication** — e.g., the .NET backend calling a Python ML sidecar for facial recognition. gRPC's binary protocol and HTTP/2 multiplexing are significantly faster than REST for high-frequency internal calls.
- **Streaming** — e.g., real-time progress updates for long-running exports. gRPC server streaming is more efficient than polling a REST endpoint.

For 50-60 concurrent staff on an internal network, REST performance is more than sufficient for all standard CRUD operations.

### How Hard Is the Hybrid Approach in ASP.NET Core?

**Very easy.** This is one of ASP.NET Core's strengths — REST controllers and gRPC services coexist in the same project, same process, same port.

```csharp
// Program.cs — both REST and gRPC served from the same app
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers();          // REST
builder.Services.AddGrpc();                 // gRPC

var app = builder.Build();

app.MapControllers();                       // REST endpoints
app.MapGrpcService<SatsangiSyncService>();  // gRPC service
app.UseGrpcWeb();                           // grpc-web for browser clients (if needed)

app.Run();
```

**Key points about the hybrid approach:**

- **Same service layer.** Both REST controllers and gRPC services inject and call the same business logic services (e.g., `ISatsangiService`). No code duplication.
- **Same DI container.** Authentication, EF Core `DbContext`, caching, background services — all shared.
- **Incremental adoption.** You can add a single gRPC service for one hot path (e.g., bulk sync) without touching any existing REST endpoints.
- **No infrastructure changes.** No proxy container, no separate port. Kestrel (ASP.NET Core's built-in server) handles HTTP/1.1 (REST), HTTP/2 (gRPC), and grpc-web simultaneously.
- **Effort to add a gRPC endpoint:** Define a `.proto` file for that specific service, run `Grpc.Tools` codegen, implement the service class (which delegates to the same service layer). Roughly 1-2 hours per endpoint.

| Aspect | REST (Phase 1) | gRPC (Added as needed) |
|---|---|---|
| Browser support | Native (JSON over HTTP/1.1) | Requires grpc-web middleware |
| Debugging | Browser DevTools, curl, Swagger | Binary payloads, needs grpcurl or AI tooling |
| Payload size | Larger (JSON text) | ~2.5x smaller (Protobuf binary) |
| Serialization speed | Adequate for 50-60 users | ~10x faster (matters at high volume) |
| Streaming | Polling or WebSocket | Native server/client/bidirectional streaming |
| Code generation | None needed | `.proto` + `Grpc.Tools` |
| Add to existing project | N/A (already there) | 1-2 hours per endpoint, zero infra changes |

**Container count (unchanged):**

| Component | .NET Stack |
|---|---|
| Edge Web Server (Caddy/Nginx) | 1 container |
| ASP.NET Core (REST + background workers) | 1 container |
| **Total on Compute Node** | **2 containers** |

---

## 3. ORM (Entity Framework Core) vs Stored Procedures

> **TL;DR:** Entity Framework Core is overwhelmingly the modern .NET best practice for data access. We will use EF Core as the primary data layer, with escape hatches to raw SQL for specific heavy operations.

**The Context:**
Historically, enterprise .NET applications favored stored procedures for all database access — business logic lived in the database, and the application was a thin UI layer. Modern .NET has shifted decisively toward ORM-first development.

### Entity Framework Core (EF Core)

EF Core is an ORM that maps C# classes directly to PostgreSQL tables:

- **Code-First Migrations:** Define your schema in C# classes. EF Core generates migration SQL automatically. Schema changes are version-controlled alongside application code.
- **LINQ Queries:** Write database queries in C# with full IntelliSense and compile-time checking. No raw SQL strings that can silently break.
- **Change Tracking:** EF Core tracks which properties you modified and generates optimized `UPDATE` statements — only the changed columns are written.
- **Strongly Typed:** If you rename a column in the model, the compiler tells you every query that broke. With stored procedures, you discover this at runtime.
- **Async-First:** All EF Core operations have native `async` variants (`ToListAsync()`, `SaveChangesAsync()`), integrating cleanly with ASP.NET Core's async pipeline.

### Stored Procedures

Stored procedures still have valid use cases:

- **Bulk Operations:** Inserting or updating 100,000+ legacy records during ETL migration. EF Core's change tracker adds overhead per-entity that is wasteful for bulk loads.
- **Complex Reporting Queries:** Multi-table aggregations with CTEs, window functions, or recursive queries that are more naturally expressed in SQL than LINQ.
- **Database-Level Security:** In highly regulated environments where the DBA controls exactly which SQL statements can execute. Not a concern for our internal app.

### Our Approach

- **Primary:** EF Core for all standard CRUD operations, migrations, and business queries. This covers 90%+ of data access.
- **Escape Hatch:** Raw SQL via `context.Database.ExecuteSqlRawAsync()` or Dapper for specific bulk ETL operations and complex reporting queries where EF Core's abstraction adds unnecessary overhead.
- **No Stored Procedures for Business Logic:** Business rules live in C# code, not in the database. This keeps logic testable, version-controlled, and debuggable.

---

## 4. Background Task Processing in .NET

> **TL;DR:** .NET provides built-in mechanisms for background task processing — no external queue infrastructure needed for Phase 1. For durable, persistent tasks, we can add Hangfire (PostgreSQL-backed) without introducing Redis or RabbitMQ.

**The Problem:**
Certain operations take too long for a request-response cycle:
1. Exporting 50,000 user records to CSV.
2. Bulk ETL migration of 200,000 legacy records.
3. Generating thumbnails or compressing uploaded images.
4. Sending bulk notifications.

**Why .NET Handles This Natively:**
True multi-threading in .NET means a background task runs on a separate thread within the same process without blocking the web request threads. This eliminates the need for a separate worker container or external queue infrastructure for many workloads.

### Built-in Options

**`BackgroundService` (Hosted Service):**
A long-running service that starts with the application and runs in the background. Ideal for continuous processing (e.g., polling a queue, processing uploads).

```csharp
public class ExportWorker : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        while (!stoppingToken.IsCancellationRequested)
        {
            var job = await _channel.Reader.ReadAsync(stoppingToken);
            await ProcessExportAsync(job);
        }
    }
}
```

**`Channel<T>` (In-Memory Queue):**
A thread-safe, bounded producer/consumer queue built into .NET. The gRPC handler writes a job to the channel; the `BackgroundService` reads and processes it.

- *Pros:* Zero infrastructure. No external dependencies. Extremely fast.
- *Cons:* In-memory only — if the process crashes, pending jobs are lost.

### Durable Option: Hangfire

For tasks that must survive server restarts (e.g., scheduled reports, deferred notifications), **Hangfire** provides:
- PostgreSQL-backed persistence (no Redis needed).
- Automatic retries with exponential backoff.
- A built-in web dashboard for monitoring job status.
- Scheduled/recurring jobs (e.g., "generate weekly report every Monday at 6 AM").

### Our Approach (Phased)

- **Phase 1:** `BackgroundService` + `Channel<T>` for real-time task offloading (CSV exports, image processing). Simple, zero infrastructure.
- **If durability is needed:** Add Hangfire with PostgreSQL storage. No new infrastructure — it uses the existing database.
- **Phase 2 (High Scale):** If task volume exceeds thousands per hour or if we need distributed workers across multiple servers, evaluate Redis-backed queues (e.g., MassTransit or raw Redis Streams).

---

## 5. Object Storage vs File Storage

> **TL;DR:** We will use S3-compatible object storage for all media files (photos, ID proofs, Form C documents). Object storage provides pre-signed URL uploads, native versioning, and a clean cloud migration path that file storage cannot match.

**The Context:**
The system stores ~500GB of media data across up to 500,000 registrations. This includes profile photos, ID proof scans, and Form C documents for foreign nationals. 50-60 concurrent staff members upload files during registration.

### Why Object Storage Wins

**1. Pre-Signed URL Uploads (Backend Bypass):**
With object storage, the backend generates a short-lived, pre-signed URL. The browser uploads the file *directly* to the storage server via a standard HTTP `PUT`. The .NET backend never touches the file bytes — it stays free to serve other gRPC requests.

With file storage, every upload flows through the backend process: the browser sends multipart data to the API, the API writes to disk. With 50 staff uploading simultaneously, the backend becomes the bottleneck.

**2. Built-in Access Control:**
Pre-signed URLs are time-limited (e.g., 5 minutes) and scoped to a specific object key. There is no need to build auth middleware for file downloads — the URL itself is the access token. Expired URLs simply stop working.

With file storage, you must either:
- Proxy every download through the backend (adding load), or
- Configure Nginx `X-Accel-Redirect` rules with auth checks (complex and fragile).

**3. Native Versioning:**
Object storage supports bucket-level versioning. When a satsangi's photo is updated, the previous version is automatically preserved with a version ID. You can retrieve any historical version at any time.

File storage has no equivalent. To preserve history, you must build custom logic: rename the old file (e.g., `photo_v1.jpg`, `photo_v2.jpg`), manage a version metadata table, and handle cleanup. This is error-prone and adds application complexity.

**4. Satsangi Blocking & Audit Trail:**
When a satsangi is restricted from physical entry (blocked), their profile photo and identity documents must remain immutably stored for identification at checkpoints (QR scan or facial recognition at gates). Object storage versioning guarantees that:
- The original photo used for identification is always retrievable, even if the profile is later updated or deactivated.
- A complete audit trail of document changes exists without any custom application code.
- Security staff at entry gates always have access to the verified, original identity media.

**5. Backup Advantages:**
Object storage servers provide built-in replication and sync tools (e.g., `mc mirror` for MinIO, `weed filer.sync` for SeaweedFS). Backing up 500GB of small files via `rsync` is notoriously slow due to per-file metadata overhead and race conditions during active writes.

**6. Cloud Migration Readiness:**
Because the application interacts with storage via the S3 API (PutObject, GetObject, GeneratePresignedUrl), migrating from self-hosted object storage to AWS S3 requires changing a single endpoint URL in the environment configuration. Zero code changes. With file storage, migration to cloud requires rewriting every upload/download path to use the AWS SDK.

---

## 6. Object Storage Choice: SeaweedFS

> **TL;DR:** We will use **SeaweedFS** as our self-hosted S3-compatible object storage. It is Apache 2.0 licensed (no AGPL risk), S3-compatible, lightweight, and uses the same AWS S3 SDK — making future migration to AWS S3 a config change.

### Why Not MinIO?

MinIO is the most popular self-hosted S3-compatible storage, but two factors disqualify it for our long-term use:
- **AGPL v3 License:** MinIO switched from Apache 2.0 to GNU AGPL v3 in 2021. For internal-only deployment (Phase 1), AGPL's network interaction clause is unlikely to trigger. However, when public registration (Phase 2) goes live, public users will interact directly with the storage server via pre-signed URL uploads/downloads. Under AGPL Section 13, this creates a source code disclosure obligation. While manageable if running unmodified MinIO, it introduces unnecessary legal complexity.
- **Repository Risk:** The MinIO GitHub repository has moved toward a more restrictive contribution model with reduced community participation, increasing bus-factor risk for long-term reliance.

### Other Alternatives Considered

- **Garage** (AGPL v3) — Designed for geo-distributed storage across unreliable nodes. Overengineered for our single-server topology. Same AGPL concern as MinIO.
- **Azure Blob Storage / Azurite** — First-class .NET SDK, but ties us to Azure cloud. Azurite is a dev emulator, not a production engine. Does not meet our self-hosted requirement.

### Why SeaweedFS

- **License:** Apache 2.0 — permissive, no copyleft, no source disclosure obligations. Safe for both internal and public-facing use.
- **S3 Compatibility:** Provides an S3 API gateway (`weed s3`) supporting pre-signed URLs, bucket versioning, and multi-part uploads.
- **Architecture:** Lightweight single binary with a master + volume server topology. Runs comfortably on a single machine for our 500GB scale.
- **Backup:** Built-in async replication and `weed filer.sync` for continuous mirroring to the backup server.
- **.NET SDK:** Uses the standard AWS S3 SDK (`AWSSDK.S3`) — the exact same code works against SeaweedFS, MinIO, or AWS S3. Switching storage backends is a config change, not a code change.
- **Maturity:** Active development since 2015, 25k+ GitHub stars. Used in production at petabyte scale.

| Criteria | SeaweedFS (Chosen) | MinIO | Garage | Azure Blob |
|---|---|---|---|---|
| License | Apache 2.0 ✅ | AGPL v3 ⚠️ | AGPL v3 ⚠️ | Proprietary ❌ |
| S3 Compatibility | Good (via S3 gateway) | Excellent | Good | Different API |
| Pre-signed URLs | ✅ | ✅ | ✅ | ✅ (SAS tokens) |
| Versioning | ✅ | ✅ | Limited | ✅ |
| Single-server fit | ✅ | ✅ | Overengineered | Not self-hosted |
| .NET SDK | AWS S3 SDK | AWS S3 SDK | AWS S3 SDK | Azure SDK |
| Maturity | High | Very high | Medium | Very high |

---

## 7. Authentication Strategy (Phased)

> **TL;DR:** Phase 1 uses ASP.NET Identity for the registration app's 100-200 staff users. When additional org apps (pledge, donation, accommodation) come online, we evaluate adding OpenIddict (free, .NET-native SSO) or migrating to Keycloak (no-code SSO hub).

**The Context:**
The original architecture specified Keycloak as a centralized SSO Identity Provider. With the move to .NET, we have the option to use ASP.NET Identity — the framework's built-in user management system — which eliminates an external dependency for Phase 1.

### Phase 1: ASP.NET Identity (Single App)

ASP.NET Identity provides:
- **User Management:** Registration, login, password hashing (bcrypt/PBKDF2), account lockout, email confirmation, password reset — all built-in.
- **Role-Based Authorization:** Define roles (Admin, Staff, ReadOnly) and protect gRPC/API endpoints with `[Authorize(Roles = "Admin")]`.
- **JWT Bearer Authentication:** Issue JWTs from the .NET backend. The same backend validates them on every request via `AddAuthentication().AddJwtBearer()`.
- **EF Core Integration:** User data is stored in PostgreSQL via EF Core — the same database and ORM as the rest of the application. No separate identity database.
- **No External Infrastructure:** No Keycloak container to deploy, configure, back up, or update. Authentication lives inside the application.

**What ASP.NET Identity Does NOT Provide:**
- **SSO across multiple applications.** ASP.NET Identity is per-application. If a staff member logs into the registration app, they are not automatically logged into the pledge app. Each app would have its own login screen and its own user table.
- **OIDC/OAuth2 Provider.** ASP.NET Identity manages users but does not act as an OpenID Connect Identity Provider. Other apps cannot delegate authentication to it without additional libraries.
- **No-Code Admin Console.** User management requires building custom admin pages or using the `dotnet-aspnet-codegenerator` scaffolding.

**For Phase 1, this is sufficient.** We have one application and 100-200 staff users. The simplicity of keeping auth inside the app (no external containers, no OIDC protocol complexity) outweighs the SSO limitation.

### Phase 2: SSO for Multiple Org Apps

When the organization builds additional apps (pledge, donation, accommodation), staff members should log in once and access all apps. Two paths are available:

**Option A: ASP.NET Identity + OpenIddict**
- **What it is:** OpenIddict is a free, open-source library that adds OpenID Connect server capabilities on top of ASP.NET Identity. The registration app's backend becomes the central OIDC provider.
- **How it works:** Other org apps (built in any language) redirect to the registration app's login page for authentication, receive a JWT, and use it for API access.
- **Pros:** Free. Fully .NET-native. Reuses the existing ASP.NET Identity user store — no user migration. The registration app evolves into the SSO hub.
- **Cons:** Requires building a custom login/consent UI. Requires building an admin dashboard for managing app clients. More development work than a turnkey solution.

**Option B: Migrate to Keycloak**
- **What it is:** Keycloak is a standalone Identity Provider (maintained by Red Hat) with a no-code Admin Console, pre-built login pages, and full OIDC/SAML support.
- **How it works:** Deploy Keycloak as a separate Docker container. Migrate users from ASP.NET Identity's PostgreSQL tables to Keycloak's user store. All apps (registration, pledge, donation) become OIDC clients that redirect to Keycloak for login.
- **Pros:** Zero custom SSO code. Fully featured admin console. Battle-tested at enterprise scale. Supports SAML if ever needed.
- **Cons:** Requires deploying and maintaining a separate Java-based container. User migration from ASP.NET Identity to Keycloak. Heavier infrastructure.

### Migration Path Design

To ensure Phase 1 does not create a rewrite burden for Phase 2, we design with abstraction:

1. **Abstract the auth layer.** All authentication/authorization logic goes through a service interface (e.g., `IAuthService`, `ICurrentUser`). The gRPC interceptors and API endpoints never directly reference ASP.NET Identity classes.
2. **Standard JWT claims.** Use standard OIDC claim names (`sub`, `email`, `roles`) from day one, even though ASP.NET Identity issues the JWTs. When we migrate to OpenIddict or Keycloak, the JWT structure remains identical — downstream code does not change.
3. **No business logic in the identity layer.** User roles and permissions are enforced by the application, not by the identity provider. Switching the identity backend (Identity → OpenIddict → Keycloak) only changes where the JWT comes from, not how it's used.

---

## 8. Caching Strategy in .NET

> **TL;DR:** We use a multi-tiered caching strategy identical in concept to the Python-era plan, but leveraging .NET's built-in abstractions. Redis is deferred to Phase 2.

### Tier 1: Browser-Side Caching (React Query)
Unchanged from the original architecture. `@tanstack/react-query` caches server responses in the browser's RAM. Repeated requests for static data (Country → State dropdowns) are served instantly from the client without a network round-trip.

### Tier 2: In-Process Server Caching (`IMemoryCache`)
.NET's built-in `IMemoryCache` replaces Python's `@lru_cache`:
- Supports configurable expiration (absolute and sliding).
- Supports size limits to prevent unbounded memory growth.
- Thread-safe — shared across all request threads within the process.

Unlike Python's `@lru_cache` (which was per-process with no invalidation), `IMemoryCache` in .NET is shared across all threads in the single ASP.NET Core process and supports explicit invalidation and TTL-based expiry.

### Tier 3: Distributed Caching (Phase 2 — Redis)
.NET provides the `IDistributedCache` interface. In Phase 1, we code against this interface using the in-memory implementation. When Redis is introduced in Phase 2, we swap the implementation via DI configuration — zero application code changes.

```csharp
// Phase 1: In-memory (no Redis needed)
builder.Services.AddDistributedMemoryCache();

// Phase 2: Redis (one-line swap)
builder.Services.AddStackExchangeRedisCache(options =>
{
    options.Configuration = "redis:6379";
});
```

This approach ensures we never hardcode caching assumptions while avoiding premature infrastructure complexity.
