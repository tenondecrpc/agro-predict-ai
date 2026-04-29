# Tasks: Deployment Profiles

---

## User Story 1 - Connected Kubernetes deployment (Priority: P1)

### US1-T1: Define deployment profile models
- **Verify**: HPAConfig, HealthProbe, ResourceQuota models

### US1-T2: Implement profile detection
- **Verify**: Detect connected vs air-gapped from env

---

## User Story 2 - Air-gapped deployment (Priority: P2)

### US2-T1: Implement air-gapped validation
- **Verify**: Reject external URLs in air-gapped mode

---

## User Story 3 - HPA configuration (Priority: P3)

### US3-T1: Define HPA config model
- **Verify**: Min/max replicas, scale thresholds

---

## Verification & Archive

### V-T1: Run lint
### V-T2: Run all deployment tests
### V-T3: Archive
