# Feature Specification: Security and Secrets

**Feature Branch**: `010-security-secrets`  
**Created**: 2026-04-28  
**Status**: Implemented  
**Input**: Vault integration, envelope encryption, credential rotation SLA, and dual-control break-glass

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Secrets management with Vault (Priority: P1)

All credentials (database passwords, API keys, encryption keys, OAuth secrets) are stored in HashiCorp Vault or External Secrets Operator. The application retrieves secrets at runtime through secure API calls. No credentials are stored in application config, environment variables committed to Git, frontend bundles, or logs.

**Why this priority**: Credential exposure is a critical security risk. Vault integration ensures secrets are managed securely and rotated regularly.

**Independent Test**: Can be fully tested by deploying with Vault, verifying the application retrieves secrets at startup, and confirming no secrets appear in logs or config files.

**Acceptance Scenarios**:

1. **Given** Vault is configured with secrets, **When** the application starts, **Then** it retrieves all required secrets from Vault and starts successfully.
2. **Given** a secret is rotated in Vault, **When** the application's credential refresh cycle runs, **Then** it uses the new secret without downtime.
3. **Given** Vault is unavailable at startup, **When** the application attempts to start, **Then** it fails with a clear error message indicating the missing secrets.

---

### User Story 2 - Envelope encryption for sensitive data (Priority: P2)

Sensitive data stored in PostgreSQL (tenant credentials, API keys, prediction results containing PII) is encrypted at rest using envelope encryption. Each data item is encrypted with a data encryption key (DEK), which is itself encrypted with a key encryption key (KEK) stored in Vault.

**Why this priority**: Data-at-rest encryption protects sensitive information from unauthorized access if the database is compromised.

**Independent Test**: Can be tested by storing sensitive data, verifying it is encrypted in the database, and confirming it can be decrypted correctly by the application.

**Acceptance Scenarios**:

1. **Given** sensitive data is stored, **When** the database is queried directly, **Then** the data appears as encrypted ciphertext.
2. **Given** encrypted data is retrieved by the application, **When** the application decrypts it, **Then** the original plaintext is recovered correctly.
3. **Given** the KEK is rotated, **When** existing encrypted data is accessed, **Then** the system re-encrypts the DEK with the new KEK transparently.

---

### User Story 3 - Credential rotation and dual-control break-glass (Priority: P3)

Credentials are rotated on a configurable schedule (SLA). In emergency situations, a dual-control break-glass process allows two authorized operators to jointly access or rotate credentials. All break-glass events are audited.

**Why this priority**: Credential rotation limits the window of exposure for compromised credentials. Dual-control break-glass ensures emergency access is available but auditable and not easily abused.

**Independent Test**: Can be tested by triggering a credential rotation, verifying the old credentials are invalidated, and testing the break-glass process with two operators.

**Acceptance Scenarios**:

1. **Given** a credential rotation SLA is configured, **When** the rotation schedule triggers, **Then** the credential is rotated and all services update to the new credential.
2. **Given** a break-glass request is initiated, **When** a second authorized operator approves, **Then** the break-glass access is granted and the event is audited.
3. **Given** a break-glass request has only one approval, **When** the request is evaluated, **Then** access is denied until the second approval is received.

---

### Edge Cases

- What happens when Vault is permanently unavailable (not just a transient failure)?
- How does the system handle a KEK compromise (requires re-encryption of all DEKs)?
- What happens when the break-glass process is initiated but the second approver is unavailable?
- How does the system handle credential rotation during an active prediction pipeline execution?
- What happens when the envelope encryption library has a vulnerability (dependency risk)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST store all credentials in HashiCorp Vault or External Secrets Operator.
- **FR-002**: System MUST NOT store credentials in application config, environment variables committed to Git, frontend bundles, or logs.
- **FR-003**: System MUST implement envelope encryption for sensitive data at rest in PostgreSQL.
- **FR-004**: System MUST encrypt data encryption keys (DEKs) with key encryption keys (KEKs) stored in Vault.
- **FR-005**: System MUST support credential rotation on a configurable schedule (SLA).
- **FR-006**: System MUST support dual-control break-glass for emergency credential access.
- **FR-007**: System MUST audit all break-glass events with timestamp, operators, and action taken.
- **FR-008**: System MUST invalidate old credentials immediately after rotation.
- **FR-009**: System MUST support KEK rotation with transparent DEK re-encryption.
- **FR-010**: System MUST fail securely when Vault is unavailable (no fallback to plaintext credentials).

### Key Entities

- **Secret**: Represents a managed secret. Key attributes: secret_id, vault_path, secret_type, rotation_schedule, last_rotated_at, status.
- **EncryptedData**: Represents data encrypted with envelope encryption. Key attributes: data_id, encrypted_payload, encrypted_dek, kek_version, created_at, tenant_id.
- **BreakGlassEvent**: Represents a dual-control break-glass event. Key attributes: event_id, requested_by, approved_by_1, approved_by_2, action_taken, timestamp, audit_log_ref.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero credentials appear in logs, config files, or Git history (verified by secret scanning tools).
- **SC-002**: Credential rotation completes within the configured SLA for 100% of scheduled rotations.
- **SC-003**: Envelope encryption adds less than 10ms overhead per encrypt/decrypt operation (P95).
- **SC-004**: Break-glass events require exactly two approvals (zero single-approver break-glass events).
- **SC-005**: System fails securely when Vault is unavailable (no plaintext credential fallback, clear error message).
