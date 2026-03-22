# Architecture & Design Documents

This directory contains the Request for Comments (RFC) style Architectural Decision Records (ADRs) and strategy discussions for the JKP Registration project.

We use this structure to document the "why" behind the technologies we use, making it easier for new developers to understand our deployment topology and system architecture.

## Documents

This folder contains two types of documents:
1. **Living Documents:** (e.g., `002-architectural-choices.md`) These describe the *current* state and reasoning of the system architecture. They should be updated as the architecture evolves.
2. **Point-in-Time Reviews:** (e.g., `poc-deployment-review-22-03-2026.md`) These are historical snapshots reviewing the system at a specific date. They show how the system migrated from a POC to production over time.

* [poc-deployment-review-22-03-2026.md](./poc-deployment-review-22-03-2026.md) - A historical point-in-time review of the initial local POC setup vs the planned production architecture.
* [002-architectural-choices.md](./002-architectural-choices.md) - **(Living Document)** A team-friendly breakdown of why we chose gRPC, Edge Web Servers, and self-hosted PostgreSQL.
* [003-web-hosting-concepts.md](./003-web-hosting-concepts.md) - **(Living Document)** A beginner-friendly guide explaining CORS, Origins, Reverse Proxies, and why CDNs aren't needed for this internal application.
