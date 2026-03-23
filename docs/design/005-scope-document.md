# Project Scope Document

This document outlines the scope, target audience, and feature boundaries for the JKP Registration system to prevent feature creep and align development efforts.

## Target Audience & Scale
- **Total User Base:** ~20 designated staff members.
- **Concurrent Usage:** 5-7 active users at any given time.
- **Geography:** Distributed across 4-5 different geographical locations within India.
- **Primary Use Case:** Web-based data entry and retrieval.

## Phase 1: Staff Registration Tool (Current Focus)
The primary objective of Phase 1 is to replace legacy systems with a modern, fast, and type-safe registration flow.

**In-Scope:**
- Responsive Web Application (React) accessible via PC, Tablet, and Mobile browsers.
- Multi-step registration workflow for new Satsangis.
- Secure, VPN-less remote access for the ~20 staff members using Cloudflare Zero Trust (Email OTP). This avoids the overhead of building a custom in-house authentication system.
- Self-hosted PostgreSQL database.
- Automated interval backups (e.g., 3-hour `pg_dump` snapshots) stored on a separate in-house server for redundancy.
- gRPC backend for strict type-safety and high performance.

**Out-of-Scope for Phase 1:**
- Public self-registration.
- Native mobile applications (iOS/Android).
- Complex centralized organization-wide SSO.

## Phase 2: Public Expansion (Future Capability)
The architecture designed in Phase 1 intentionally supports these future requirements without requiring a foundational rewrite.

**Planned Features:**
- **Public Self-Registration:** Opening specific web routes (like `/register`) to the public, shielded by Cloudflare's Web Application Firewall (WAF) to absorb malicious traffic.
- **Centralized Authentication:** Transitioning from Cloudflare Email OTP to a centralized organization-wide SSO/Identity Provider to ensure login consistency across all company apps.
- **Cloud Database Migration:** Transitioning the self-hosted PostgreSQL database to a managed public cloud (e.g., AWS RDS) simply by updating environment variables.
- **Enhanced Backup Strategy:** Upgrading from local interval snapshots to off-site cloud backups or continuous WAL (Write-Ahead Logging) archiving for Point-in-Time Recovery.
