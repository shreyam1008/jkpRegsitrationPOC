# Project Plan — Features, Policies & Roadmap

Last updated: 28 March 2026
Status: Living document — update as decisions evolve.
Companion doc: [`tech-stack.md`](./tech-stack.md) — technology choices, architecture, concurrency model & scaling.

This document captures the **product-level** plan for the JKP Registration system — features, UX decisions, operational policies, and the roadmap. It consolidates decisions from team discussions (including the March 26, 2026 review with Sundaram Bhaiya).

For all technology stack details, versions, architecture diagrams, and implementation internals, see [`tech-stack.md`](./tech-stack.md).

---

## 1. Authentication & MFA Policy

We use **Keycloak** (self-hosted, open-source SSO by Red Hat). Not rewriting auth from scratch. Expandable ashram-wide for all internal apps.

- **MFA via authenticator app** (Google Authenticator etc.). No SMS/email OTP.
- **Super admins:** MFA on **every login**.
- **Agents:** MFA **once per day**.
- **Dynamic toggle:** Super admin can relax MFA intensity during high-traffic events (e.g., Guru Poornima).

---

## 2. Media & Photo Handling

- **Storage:** Self-hosted **MinIO** (S3-compatible object storage).
- **Upload:** Client gets a pre-signed URL from backend → uploads directly to MinIO via HTTP `PUT`, bypassing the Python server.
- **Format:** Convert originals to efficient format (WebP or AVIF) on the client before upload.
- **Server-Side Processing:** Background worker creates **two versions**:
  1. **Original** — full resolution, stored as-is.
  2. **Thumbnail** — compressed to ~50 KB. Used for quick profile views and Form C.
- **In-App:** Zoom, edit, and crop photos (reference: Form C photo flow).
- Thumbnail served by default; full-size on click or download.

---

## 3. Roles, Rights & Access Control

A dynamic, configurable **Roles + Rights** system:

- **Roles** (examples): `super_admin`, `admin`, `agent`, `reader`, `auditor`.
- **Rights** (examples): `can_see_payments`, `can_delete_person`, `can_merge_records`, `can_do_everything`.
- **Dynamic Assignment:** Super admin assigns/revokes which rights belong to which roles at runtime — no code changes.
- **Enforcement:** Checked at the gRPC servicer layer on every request.

---

## 4. Audit Trail & Observability

- **Audit Log:** Every major action (create, update, delete, merge, role change) recorded with timestamp, actor, action, and before/after state.
- **Pruning Strategy:** TBD — archival, partitioning, retention policies for managing growth.
- **Viewing:** Dedicated UI for searching/browsing the audit trail (filterable by user, action, date range).
- **Error Tracking:** Sentry for application-level crash reporting and alerting.
- **Observability (TBD):** Evaluate Grafana + Prometheus for system-level monitoring in a later phase.

---

## 5. Lookup Tables & Soft Deletes

### Lookup Tables (CRUD by Super Admin)
- All lookup/reference tables (countries, states, districts, zones, categories) are **CRUD-manageable** by super admin through the UI — reducing developer dependency.
- Certain fields are **locked** (bound to code logic): roles, core countries (India, Nepal), etc.
- Countries, states, districts are **referenced by ID** throughout, never by name string.

### Soft Deletes
- **All deletes are soft deletes.** Records marked with `deleted_at` timestamp, never physically removed.
- Hard purge (if ever needed) is a super admin + audit-logged operation.

---

## 6. Caching Strategy

- **Backend:** `lru_cache` in-memory for static data (country lists, lookups). Works for single-process. No Redis in Phase 1.
- **Frontend:** TanStack Query for server-state caching. Local satsangi list cache loaded into browser RAM for instant Fuse.js fuzzy search. TBD: sync strategy and memory footprint.

---

## 7. Search & Auto-Fill

### Address Auto-Fill
- **Pincode** entered → auto-fill country, state, district, city (at least India, potentially all countries).
- **Place name** entered → auto-fill all other address details.
- Use **combobox** (not dropdown) for these fields — allows both typing and selecting.

### Recommended/Frequent Values
- Countries show **recommended first** (India, Nepal, US, Australia) — covers ~90% of cases.
- Same pattern for cities and other high-frequency fields.

---

## 8. UX & Power User Features

### Keyboard-First Design
- Full **hotkey** support for power users.
- `Tab` navigates to the **exact next logical field** — no ambiguity.
- Clear **visual indicators** for focused/active elements.

### Cart System
- **Cart/draft concept** for persistent in-progress data. Navigating away or closing the browser mid-registration preserves work.

### Print Flow
- Print can be **previewed** or **sent directly to printer** without preview — shortcut for experienced users.
- Printer, webcam, and hardware setup should be **zero-friction** from within the app. Provide a downloadable binary/installer if external setup needed.

### Merge Records
- Super admin can **merge two satsangi records** (duplicates or historical mistakes).
- UI allows **pick-and-choose** of fields between the two records.
- Merged record **sent for approval** with pledge/payment reconciliation.

### Form C Auto-Fill
- Improve the existing Form C auto-fill flow with better field mapping and photo handling.

---

## 9. Data Import (Excel)

- Provide a **downloadable Excel template** with all fields strictly matching our validation schema.
- User uploads → data loads into a **table-like preview in the browser**.
- All rows pass through **frontend validation** before submission to backend.
- **Never** send raw Excel directly to backend.

---

## 10. QR Code & Facial Recognition (Phase 2)

- QR code and/or facial recognition at **entry counters and exit gates** for automatic visit tracking.
- Incentivized through **food coupons** — grants exit food upon scan.
- Auto-opens the person's profile on scan.

---

## 11. Security & Secrets Management

### Secrets
- **NEVER hardcode** secrets — no IPs, tokens, passwords, or connection strings in code.
- Use `.env` files for local/dev and production.
- Evaluate **vaults** (1Password, HashiCorp Vault, or Keycloak's credential store) for pulling secrets at runtime.

### Network
- All access via **Site-to-Site VPN** across all 5 ashrams (Mangarh, Barsana, Vrindavan, Delhi, Mussoorie).
- Internal DNS: `registration.jkp.internal`.
- Application is **invisible** to the public internet.

### Aadhar Card Warning
- Registration team confirms: **Aadhar card data is not accurate** — cannot be treated as source of truth.
- Build a system/workflow to handle discrepancies (manual verification step, flagging mismatches).

---

## 12. API Design Principles

- **Not chatty:** One API call per user action. Bundle sub-operations into a single gRPC call; orchestration happens server-side.
- **Background for heavy work:** Job queues for encrypting documents, bulk exports, image processing. Never long-running HTTP connections.
- **Transactions on primary DB only.** Read replicas for analytics/reporting.

---

## 13. Deadlock Prevention

- **Consistent table access ordering** across all SQL queries and transactions.
- All queries touching multiple tables acquire locks in the **same predefined order**.

---

## 14. Testing Strategy

### Test Discipline
- Every feature must have accompanying tests covering **all edge cases**.
- On every release: **all previous + new tests must pass** before merge to main (production branch).
- No merge without green CI. Local vs GitHub Actions runner — TBD.
- Contract testing for gRPC interfaces — TBD.

For test tooling and layer details, see [`tech-stack.md` → Testing](./tech-stack.md#testing).

---

## 15. Code Quality & Enforcement

### Pre-Commit Checks (enforced via Husky or equivalent)
- No **magic variables** (unexplained literals).
- No **god files** (1000+ lines).
- No **unused variables** or **zombie code** (dead/commented-out code).
- **Cyclomatic Complexity Cap (CCC)** — functions must stay under a defined complexity threshold.
- No `console.log` in production builds.
- No **unhandled errors** — every catch block must log or propagate.
- All linting and formatting checks must pass before commit.

### Naming Conventions
- **Variables:** Clear, verbose **nouns** (`satsangiList`, `registrationCount`).
- **Functions:** Clear **action verbs** (`fetchSatsangi`, `validateAddress`, `mergeRecords`).
- Code should be self-explanatory without comments. Comments reserved for:
  - Clarifying genuinely complex logic.
  - Documenting crucial functions.
- All functions must have a **short docstring**.

### Documentation
- Document all major decisions as we code (this `docs/` directory).
- Keep docs in sync with implementation.

---

## 16. Target Environment

| Constraint | Value |
|---|---|
| **Browser** | Chrome (January 2026 update or newer) |
| **Hardware** | PC with 4 GB RAM minimum |
| **Locations** | 5 ashrams: Mangarh, Barsana, Vrindavan, Delhi, Mussoorie |
| **Concurrent Users** | ~50–60 active, ~100–200 total staff |

---

## 17. Docker Policy

- **Do NOT use Alpine images** for production. Use **full** or **slim** base images.
- **Reason:** glibc support required. Alpine uses musl-c, causing subtle compatibility issues.

---

## 18. Backup Strategy

### Database (PostgreSQL)
1. Scheduled `pg_dump` snapshots (e.g., every 3 hours).
2. Compress with **zstd** (high compression ratio, fast).
3. Store on **two disks:** same PC (local) + another PC over network (SSH/SCP).
4. Continuous WAL streaming to secondary server (analytics replica + fast recovery).

### Media (MinIO)
- **Incremental backups** to a separate drive/server.
- MinIO's built-in mirroring for continuous sync.

### Staging
- Staging server is **NOT backed up** — only holds synthetic test data.

---

## 19. Multi-Ashram Deployment

- Must work **seamlessly across all 5 ashrams**.
- Connected via **Site-to-Site VPN**.
- Single deployment serves all locations via internal DNS (`registration.jkp.internal`).
- Edge cases: handle intermittent VPN connectivity gracefully (offline-capable flows TBD).
