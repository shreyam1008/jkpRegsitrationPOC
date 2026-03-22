# Architecture & Design Documents

This directory contains the Request for Comments (RFC) style Architectural Decision Records (ADRs) and strategy discussions for the JKP Registration project.

We use this structure to document the "why" behind the technologies we use, making it easier for new developers to understand our deployment topology and system architecture.

## Documents

* [001: Deployment Review](./001-deployment-review.md) - Review of the initial gRPC deployment approach vs. the target production shape (self-hosted PostgreSQL, dedicated grpc-web proxy, single-domain HTTPS).
* [002: Architectural Choices](./002-architectural-choices.md) - An "Inventor's Perspective" deep dive into why we chose gRPC, dedicated proxies, and same-domain React hosting, with a comparison to the previous local dev state.
* [003: Web Hosting Concepts](./003-web-hosting-concepts.md) - A beginner-friendly guide explaining CORS, Origins, Reverse Proxies (like Caddy/Nginx), and why CDNs aren't needed for this internal application.
