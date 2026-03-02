# SafeCopy Roadmap

This document outlines the strategic direction and developmental milestones of **SafeCopy**, evolving from a foundational I/O implementation into a modular, architecture-driven backup system.

---

## 🎯 Project Vision

To provide a highly reliable, structurally sound, and cryptographically secure backup solution that simplifies data preservation without compromising on engineering rigor or transparency.

---

## 🛤 Milestones

<small>(Not fixed, always evolving)</small>

### ✅ Phase 1: MVP & Foundation (v0.1.0 - v0.2.0)

*Focus: Establishing basic I/O and user interaction.*

- **v0.1.0: Core Functionality**
  - ✅ Folder-to-folder recursive backup engine.
  - ✅ Preliminary Flask-based Web UI for configuration.
  - ✅ JSON-backed persistent configuration.
  - ✅ Basic activity logging.
- **v0.2.0: Reliability & Optimization**
  - ✅ System tray integration for background persistence.
  - ✅ Implementation of file versioning and retention policies.
  - ✅ Archive support: ZIP (Deflate) and TAR (Gzip) compression.
  - ✅ Atomic configuration writes to prevent data corruption.

### ✅ Phase 2: Security & Automation (v0.3.0 - v0.4.0)

*Focus: Hardening the system and enhancing utility.*

- **v0.3.0: Enterprise Features**
  - ✅ Role-based authentication (RBAC) and user session management.
  - ✅ Advanced scheduling: Cron-like daily, weekly, monthly, and interval-based triggers.
  - ✅ SMTP integration for automated email notifications. (Removed in v0.5.0, planned to be re-added in v0.6.0)
  - ✅ Initial integrity verification via per-file cryptographic checksums (MD5).
- **v0.4.0: Cryptographic Hardening**
  - ✅ AES-256-GCM end-to-end encryption for all backup types.
  - ✅ Key management via system-native keyring.
  - ✅ Introduction of `SFENC1.0` magic header for encrypted payload identification.
  - ✅ Initial suite of unit tests for core modules.

### 🔄 Phase 3: Architecture Overhaul (v0.5.0 - CURRENT)

*Focus: Modularization, Scalability, and Formal Verification.*

- **Modular Backup Package**
  - ✅ Decoupled `BackupEngine` from side-effecting logic.
  - ✅ **Manifest System**: Deterministic generation of MD5 manifests embedded within archives.
  - ✅ **Formal Verification**: Post-backup integrity validation against reconstructed source manifests.
  - ✅ **Runner Orchestration**: Centralized coordination of backup → history → verification.
- **Data Persistence Layer**
  - ✅ Transition from legacy raw SQL to **SQLAlchemy ORM**.
  - ✅ Implementation of Repository and Service patterns for clean separation of concerns.
  - ✅ Strongly-typed DTOs (Pydantic) with deep field-level validation.
- **Quality Assurance**
  - ✅ Comprehensive test coverage for the `backup/` package.
  - ✅ Service-layer unit tests for all domain entities.
  - [ ] Refactor Web UI to use the new architecture.
  - [ ] Add more tests for the new architecture.

### ⏳ Phase 4: System Intelligence & Robustness (v0.6.0 - v0.7.0)

*Focus: Observability, Concurrency, and Backend Depth.*

- [ ] **Observability Dashboard**: Real-time stats, storage trends, and success/failure heatmaps.
- [ ] **Concurrency Control**: Locking mechanism for thread-safe concurrent mapping execution.
- [ ] **Write-Ahead Logging (WAL)**: Job-level logging to ensure recovery from interrupted backup cycles.
- [ ] **Plugin Interface**: Unified interface for future storage backends (Cloud/Remote).
- [ ] **Performance Benchmarking**: Comparative analysis of compression and encryption throughput.
- [ ] **SMTP integration for automated email notifications.** (Re-added in v0.6.0)

### 🚀 Phase 5: Production Readiness (v1.0.0+)

*Focus: Distribution and Stability.*

- [ ] **PyInstaller Packaging**: Standalone executable distribution.
- [ ] **Installer / Service**: Native Windows service installation and desktop shortcuts.
- [ ] **API Documentation**: Full OpenAPI/Swagger documentation for the web service.
- [ ] **Restore Pipeline**: Formal reconstructor using manifests as the single source of truth.

---

## 🏛 Feature Matrix

| Domain | Feature | Status |
| :--- | :--- | :--- |
| **Core Engine** | Recursive Backup | ✅ |
| | Versioning/Pruning | ✅ |
| | Compression (ZIP/TAR) | ✅ |
| | WAL / Job Recovery | ⏳ |
| **Integrity** | Manifest Generation | ✅ |
| | Checksum Verification | ✅ |
| | DB-backed Results | ✅ |
| **Security** | AES-256-GCM Encryption | ✅ |
| | Keyring Integration | ✅ |
| | RBAC / Sessions | ✅ |
| **Data Layer** | SQLAlchemy ORM | ✅ |
| | DTO Validation | ✅ |
| | Migration Strategy | ⏳ |
| **UI/UX** | Dashboard | ✅ |
| | Advanced Scheduler | ✅ |
| | Reporting/Stats | 🔄 |

---
