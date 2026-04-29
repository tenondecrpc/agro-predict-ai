# Feature Specification: Config Management

**Feature Branch**: `011-config-management`  
**Created**: 2026-04-28  
**Status**: Implemented  
**Input**: Versioned configuration in PostgreSQL with audit trail, rollback, and shadow-mode validation

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Versioned configuration storage (Priority: P1)

System configuration (agent parameters, model settings, data source configs, quality gate thresholds) is stored in PostgreSQL with full versioning. Every configuration change creates a new version with metadata (who changed it, when, what changed, and why).

**Why this priority**: Configuration drives system behavior. Without versioning, there is no audit trail, no rollback capability, and no way to track configuration drift.

**Independent Test**: Can be fully tested by updating a configuration value, verifying a new version is created, and checking the version history.

**Acceptance Scenarios**:

1. **Given** a configuration key exists, **When** an admin updates its value, **Then** a new version is created with the old value, new value, timestamp, and user.
2. **Given** a configuration version history exists, **When** an admin requests the history, **Then** all versions are returned in chronological order with change metadata.
3. **Given** a configuration is updated, **When** the system reads the config, **Then** it reads the latest active version.

---

### User Story 2 - Shadow-mode configuration validation (Priority: P2)

Before a configuration change becomes active, it is validated in shadow mode. The system applies the new configuration to a shadow copy of the runtime and verifies it does not cause errors, performance degradation, or policy violations. Only after shadow-mode validation passes does the change become active.

**Why this priority**: Configuration errors can cause system-wide failures. Shadow-mode validation catches misconfigurations before they affect production.

**Independent Test**: Can be tested by submitting a configuration change, verifying shadow-mode validation runs, and checking the change is activated only if validation passes.

**Acceptance Scenarios**:

1. **Given** a valid configuration change, **When** shadow-mode validation runs, **Then** the change passes validation and becomes active.
2. **Given** an invalid configuration change (e.g., negative timeout), **When** shadow-mode validation runs, **Then** the change fails validation and is not activated.
3. **Given** a configuration change that causes performance degradation in shadow mode, **When** validation runs, **Then** the change is flagged and requires manual approval.

---

### User Story 3 - Configuration rollback (Priority: P3)

An operator can rollback configuration to any previous version. The rollback creates a new version (preserving the full history) and activates the rolled-back configuration. The rollback event is audited.

**Why this priority**: When a configuration change causes issues, operators must be able to quickly revert to a known-good state.

**Independent Test**: Can be tested by updating a configuration, verifying it causes an issue, rolling back to the previous version, and confirming the system behavior reverts.

**Acceptance Scenarios**:

1. **Given** a configuration version history exists, **When** an operator initiates a rollback to a previous version, **Then** the system creates a new version with the rolled-back value and activates it.
2. **Given** a rollback is performed, **When** the audit log is checked, **Then** the rollback event is recorded with operator, target version, and timestamp.
3. **Given** a rollback target version no longer exists (deleted), **When** the operator attempts the rollback, **Then** the system rejects the request with a clear error.

---

### Edge Cases

- What happens when two operators update the same configuration key concurrently?
- How does the system handle a configuration change that is valid in shadow mode but fails in production?
- What happens when the configuration database is corrupted?
- How does the system handle configuration changes during an active prediction pipeline?
- What happens when a configuration rollback target is many versions behind the current version?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST store all configuration in PostgreSQL with full versioning.
- **FR-002**: System MUST record metadata for every configuration change: user, timestamp, old value, new value, and change reason.
- **FR-003**: System MUST validate configuration changes in shadow mode before activation.
- **FR-004**: System MUST activate configuration changes only after shadow-mode validation passes.
- **FR-005**: System MUST support configuration rollback to any previous version.
- **FR-006**: System MUST create a new version entry for rollback operations (preserving full history).
- **FR-007**: System MUST audit all configuration changes and rollbacks.
- **FR-008**: System MUST support concurrent configuration updates with optimistic locking.
- **FR-009**: System MUST expose a configuration API (`GET/POST /api/v1/config`) for reading and updating configuration.
- **FR-010**: System MUST support tenant-scoped configuration (different config per tenant).

### Key Entities

- **ConfigEntry**: Represents a configuration key-value pair. Key attributes: config_id, config_key, config_value, version, tenant_id, created_by, created_at, active.
- **ConfigVersion**: Represents a version of a configuration entry. Key attributes: version_id, config_id, old_value, new_value, changed_by, changed_at, change_reason, validation_status.
- **ConfigAudit**: Represents an audit record for a configuration change. Key attributes: audit_id, config_id, version_id, action (create, update, rollback, delete), performed_by, timestamp, details.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Configuration changes with shadow-mode validation complete within 10 seconds.
- **SC-002**: Configuration rollback completes within 5 seconds.
- **SC-003**: 100% of configuration changes have a complete audit record.
- **SC-004**: Zero configuration changes bypass shadow-mode validation.
- **SC-005**: Concurrent configuration updates are handled correctly with zero lost updates (verified by optimistic locking).
