# SafeCopy

SafeCopy is a structured, architecture-driven backup system designed for reliability and cryptographic integrity. Unlike conventional backup tools, SafeCopy ensures that every backup is cryptographically verifiable, persistently audited, and structurally isolated from orchestration logic.

> **⚠️ Refactoring in progress.** The `main` branch is undergoing a major architecture overhaul (v0.5.0).
> For the last stable release, use commit [`aed40f7e`](https://github.com/karar-hayder/SafeCopy/commit/aed40f7e9b77b22e346f55961ae8e36dfca5cefa).

## Design Principles

- **Separation of Concerns**: Backup execution, manifest generation, integrity verification, and persistence are handled by independent, testable components.
- **Integrity First**: Every backup artifact contains a deterministic manifest used for post-backup validation.
- **Production Awareness**: Atomic operations and failure semantics ensure that partially-written or corrupted artifacts are never treated as valid.
- **Cryptographic Rigor**: Implementation of authenticated encryption (AES-256-GCM) with secure key management.

## System Overview

```text
BackupConfig (source, destination, compression, encryption, user_uuid, ...)
        │
        ▼
BackupEngine                    — Atomic copy / compress / rename
        │
        ├── manifest.py         — Deterministic {size, mtime, MD5} embedded in backup
        │
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
| `engine.py` | `BackupEngine` — Handles copy, ZIP, and TAR operations. Backups are written to temporary paths and **atomically renamed** upon completion to prevent partially-written artifacts from being treated as valid. |
| `manifest.py` | Pure-function manifest generators; produces deterministic metadata for source reconstruction. |
| `verification.py` | Independent verifier that compares source state against the embedded backup manifest. |
| `runner.py` | Central orchestrator linking the engine to the DB history and verification services. |
| `cryptor.py` | AES-256-GCM authenticated encryption with a chunked format and `SFENC1.0` header. |
| `dtos.py` | Pydantic data schemas; ensures strict validation between system layers. |

### `safecopy/db/`

A robust persistence layer utilizing the **Repository and Service patterns** via SQLAlchemy ORM:

| Layer | Contents |
|---|---|
| `models.py` | Domain entities: `Mappings`, `BackupHistory`, `BackupVerification`, `BackupSchedules`, `User`. |
| `services/` | Business logic layer; handles CRUD, session management, and DTO mapping. |
| `repos/` | Data access layer; isolates ORM-specific queries. |
| `dtos/` | Pydantic models with field-level validators for strict data integrity. |

## Integrity & Security

### Deterministic Manifests

Every backup produces a `manifest.json` containing deterministic per-file metadata:

- **Byte size**
- **Last modification timestamp**
- **Cryptographic checksum** (MD5 for manifest speed; future path to SHA-256)

### Failure Semantics

The system is built with operational safety in mind:

- **Atomic Renames**: Backup files only appear in the destination once fully written and closed.
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
| Scheduling | CRON-like triggers (DAILY / WEEKLY / MONTHLY / INTERVAL) per mapping. |
| Parallelism | Concurrency managed via `ThreadPoolExecutor` in the runner. |
| Authentication | Role-based (USER / ADMIN) with session-managed protection. |
| Encryption | Hardware-accelerated AES-GCM with system keyring integration. |
| Notifications | SMTP-based alerts (Removed in v0.5.0; planned for v0.6.0) |

## Restore (Planned)

A structured restore pipeline is planned to reconstruct data from any backup artifact. The system will use embedded manifests as the single source of truth to ensure the target directory matches the captured source state exactly.

## Testing & Verification

```bash
pytest safecopy/tests/ -v
```

SafeCopy maintains a high-quality test suite covering:

- **Engine Logic**: Validating all compression and atomic move paths.
- **Integrity Layer**: Mocking source changes to ensure manifest comparison catches tampered files.
- **Service Layer**: Thoroughly testing DB interactions, constraints, and DTO validation.

## Roadmap

SafeCopy follows a phased development strategy, evolving from foundational I/O toward a modular, formally verified system.

**[View Detailed Roadmap →](ROADMAP.md)**

## License

MIT License — see [`LICENSE`](LICENSE).
