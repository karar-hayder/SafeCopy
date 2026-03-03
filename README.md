# SafeCopy

SafeCopy is a structured, architecture-driven backup system designed for reliability and cryptographic integrity. Unlike conventional backup tools, SafeCopy ensures that every backup is cryptographically verifiable, persistently audited, and structurally isolated from orchestration logic.

> **✅ Refactoring Complete.** The `main` branch has successfully transitioned to a modular architecture (v0.5.0).
> For legacy reference, see commit [`aed40f7e`](https://github.com/karar-hayder/SafeCopy/commit/aed40f7e9b77b22e346f55961ae8e36dfca5cefa).

## Design Principles

- **Separation of Concerns**: Backup execution, manifest generation, integrity verification, and persistence are handled by independent, testable components.
- **Integrity First**: Every backup artifact contains a deterministic manifest used for post-backup validation.
- **Production Awareness**: Atomic operations, failure semantics, and **Windows-optimized retry logic** ensure reliability in any environment.
- **Cryptographic Rigor**: Implementation of authenticated encryption (AES-256-GCM) with secure key management.

## System Overview

```text
BackupConfig (source, destination, compression, encryption, user_uuid, ...)
        │
        ▼
BackupEngine                    — Atomic copy / compress / rename
        │                         (with retry logic for Windows file locks)
        │
        ├── manifest.py         — Deterministic {size, mtime, MD5} embedded in backup
        │                         (Streaming re-pack for TAR/ZIP)
        ▼
runner.run_backup()             — Orchestration & Persistence
        ├── BackupHistoryService     → SQLite (Audit log)
        ├── verification.verify()   → Cryptographic comparison
        └── BackupVerificationService → SQLite (Integrity record)
```

## Architecture

### `safecopy/backup/`

| Module | Responsibility |
|---|---|
| `engine.py` | `BackupEngine` — Handles copy, ZIP, and TAR operations. Backups are written to temporary paths with **unique Job IDs** and **atomically renamed** upon completion. Includes retry mechanisms for platform-specific file locks. |
| `manifest.py` | Pure-function manifest generators; produces deterministic metadata for source reconstruction. Optimized streaming embedding for archives. |
| `verification.py` | Independent verifier that compares source state against the embedded backup manifest. |
| `runner.py` | Central orchestrator linking the engine to the DB history and verification services. |
| `cryptor.py` | AES-256-GCM authenticated encryption with a chunked format and `SFENC1.0` header. |
| `dtos.py` | Pydantic data schemas; ensures strict validation between system layers. |

### `safecopy/db/`

A robust persistence layer utilizing the **Repository and Service patterns** via SQLAlchemy ORM:

| Layer | Contents |
|---|---|
| `models.py` | Domain entities: `Mappings`, `BackupHistory`, `BackupVerification`, `BackupSchedules`, `User`. |
| `services/` | Business logic layer; handles CRUD, session management, and DTO mapping. Includes robust singleton-like access and initialization guards. |
| `repos/` | Data access layer; isolates ORM-specific queries. |
| `dtos/` | Pydantic models with field-level validators for strict data integrity. |

### `safecopy/scheduler/`

| Module | Responsibility |
|---|---|
| `engine.py` | Centralized scheduler engine managing all trigger types (**Minutes, Hourly, Daily, Weekly, Monthly**). Includes drive availability checks and job isolation. |

## Integrity & Security

### Deterministic Manifests

Every backup produces a `manifest.json` containing deterministic per-file metadata:

- **Byte size**
- **Last modification timestamp**
- **Cryptographic checksum** (MD5 for manifest speed; future path to SHA-256)

### Failure Semantics

The system is built with operational safety in mind:

- **Atomic Renames**: Backup files only appear in the destination once fully written and closed.
- **Retry Logic**: Handles transient `PermissionError` or `Access Denied` issues on Windows via exponential backoff.
- **Audit Gating**: If backup execution fails, no `BackupHistory` success record is written, and temporary artifacts are purged.
- **Verification Gating**: Backups are only marked as `SUCCESS` in the audit log after a post-backup integrity check passes. Encryption occurs post-verification.

### Threat Model

- **Local Hardening**: SafeCopy assumes a secure system keyring for key storage.
- **Integrity Isolation**: Verification is independent of encryption state; manifests are checked before the encryption envelope is applied.
- **Tamper Detection**: Post-write modification of the backup archive will trigger a `FAILED_VERIFICATION` status upon audit.

## Design Decisions

- **SQLite**: Selected for lightweight, zero-config embedded persistence suitable for desktop environments.
- **AES-256-GCM**: Chosen for **authenticated encryption**, providing both confidentiality and authenticity in a single pass.
- **Pydantic/SQLAlchemy**: Used to enforce a "typed" architecture, reducing runtime errors at the boundary of I/O and business logic.
- **MD5**: Selected for high-throughput deterministic manifest generation where speed is prioritized over collision resistance.

## Capabilities

| Feature | Detail |
|---|---|
| Retention | Fully configurable versioning and automated pruning logic. |
| Scheduling | Advanced triggers (**Minutes / Hourly** / DAILY / WEEKLY / MONTHLY) per mapping. |
| Parallelism | Concurrency managed via `ThreadPoolExecutor` in the runner with Job-ID path isolation. |
| Authentication | Role-based (USER / ADMIN) with session-managed protection. |
| Encryption | Hardware-accelerated AES-GCM with system keyring integration. |
| UI/UX | Modern Flask/Jinja2 interface with real-time status dashboards. |

## Restore (Planned)

A structured restore pipeline is planned to reconstruct data from any backup artifact. The system will use embedded manifests as the single source of truth to ensure the target directory matches the captured source state exactly.

## Testing & Verification

```bash
pytest safecopy/tests/ -v
```

SafeCopy maintains a high-quality test suite covering:

- **Engine Logic**: Validating all compression, manifest embedding, and atomic move paths.
- **Integrity Layer**: Catching tampered files via manifest comparison.
- **Service Layer**: Thoroughly testing DB interactions, constraints, and DTO validation.
- **Scheduler & Web**: Integration tests for all schedule types and major Web API routes.

## Roadmap

SafeCopy follows a phased development strategy, evolving from foundational I/O toward a modular, formally verified system.

**[View Detailed Roadmap →](ROADMAP.md)**

## License

MIT License — see [`LICENSE`](LICENSE).
