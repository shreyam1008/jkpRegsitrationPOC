# Project Scope Document

This document outlines the scope, target audience, and feature boundaries for the JKP Registration system to prevent feature creep and align development efforts.

## Target Audience & Scale
- **Total User Base:** 100-200 designated staff members.
- **Concurrent Usage:** 50-60 active users at any given time.
- **Geography:** Distributed across 4-5 different geographical locations within India.
- **Primary Use Case:** Web-based data entry and retrieval.

## Phase 1: Staff Registration Tool (Current Focus)
The primary objective of Phase 1 is to replace legacy systems with a modern, fast, and type-safe registration flow.

**In-Scope:**
- Responsive Web Application (React) accessible via PC and Mobile browsers.
- Multi-step registration workflow for new Satsangis.
- Application-specific authentication using a self-hosted identity provider (SuperTokens or Logto).
- Secure internal access via Site-to-Site VPN across all offices, utilizing an Internal DNS (e.g., `registration.jkp.internal`) to map domain names without public internet exposure.
- Self-hosted PostgreSQL database.
- Automated interval backups (e.g., 3-hour `pg_dump` snapshots) to a secondary in-house server. (Continuous WAL archiving is a "nice-to-have" secondary goal).
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
