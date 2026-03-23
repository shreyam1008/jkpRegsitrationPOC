# Project Scope Document

This document outlines the scope, target audience, and feature boundaries for the JKP Registration system to prevent feature creep and align development efforts.

## Target Audience & Scale
- **Staff Users:** 100-200 designated staff members (50-60 concurrent active users).
- **Data Scale:** Expected to scale up to 500,000 (5 Lakh) registration entries (Satsangis). This includes ~100,000 legacy entries to be migrated immediately. Media data (profile photos, ID proofs, Form C docs) is expected to be around 500GB.
- **Geography:** Distributed across 4-5 different geographical locations within India.
- **Primary Use Case:** Web-based data entry, rapid retrieval, and legacy data management.

## Phase 1: Staff Registration Tool (Current Focus)
The primary objective of Phase 1 is to replace legacy systems with a modern, fast, and type-safe registration flow.

**In-Scope:**
- Responsive Web Application (React) accessible via PC and Mobile browsers.
- Multi-step registration workflow for new Satsangis.
- Form C data capture and document storage specifically for the registration of foreign nationals.
- Application-specific authentication using a self-hosted identity provider (SuperTokens or Logto).
- Secure internal access via Site-to-Site VPN across all offices, utilizing an Internal DNS (e.g., `registration.jkp.internal`) to map domain names without public internet exposure.
- Two-Server Split Topology: A stateless Compute Server (App/Proxy) and a Stateful Server (PostgreSQL/MinIO).
- Self-hosted PostgreSQL database for structured data.
- Self-hosted S3-compatible object storage (MinIO) for heavy media files (photos/ID proofs).
- Dedicated Python ETL scripts for the one-time migration of 200,000 legacy registration records.
- Automated interval backups (e.g., 3-hour `pg_dump` snapshots and MinIO syncs) to a secondary in-house server. (Continuous WAL archiving is a "nice-to-have" secondary goal).
- gRPC backend for strict type-safety and high performance.

**Out-of-Scope for Phase 1:**
- Public self-registration.
- Native mobile applications (iOS/Android).
- Centralized organization-wide SSO (authentication is currently scoped only to this app).

## Phase 2: Public Expansion (Future Capability)
The architecture designed in Phase 1 intentionally supports these future requirements without requiring a foundational rewrite.

**Planned Features:**
- **Public Self-Registration:** Opening specific web routes to the public for ID-based (non-login) registration. The plan is to use a Firebase OTP mechanism to verify users without requiring them to create a persistent account.
- **Centralized Authentication:** Scaling the application-specific SuperTokens/Logto instance to become the SSO provider for all future organization apps.
- **Cloud Database Migration:** Transitioning the self-hosted PostgreSQL database to a managed public cloud (e.g., AWS RDS) simply by updating environment variables.
