# Phase 10 — API Contract (`phase_10_api_contract.md`)

## 1. Overview
This document specifies the RESTful FastAPI v1 endpoints for Claims, Endorsements, and Refunds under `/api/v1/claims`, `/api/v1/endorsements`, and `/api/v1/refunds`.

All endpoints return the standard `APIResponse[T]` envelope (`success`, `message`, `data`, `meta`).

---

## 2. Claims Endpoints (`/api/v1/claims`)

| Method & Path | Required Role Set | Request Schema | Response Schema | Status Codes |
|---|---|---|---|---|
| `POST /api/v1/claims` | `CLAIM_CREATE_ROLES` | `ClaimIntimateRequest` | `APIResponse[ClaimResponse]` | `201 Created` (`200 OK` on idempotent replay), `403`, `404`, `409`, `422` |
| `GET /api/v1/claims` | `CLAIM_READ_ROLES` | Query: `transaction_id`, `policy_no`, `claim_status`, `claim_type`, `branch_id`, `agent_id`, `limit`, `offset` | `APIResponse[ClaimListResponse]` | `200 OK`, `403` |
| `GET /api/v1/claims/{claim_id}` | `CLAIM_READ_ROLES` | Path: `claim_id` | `APIResponse[ClaimResponse]` | `200 OK`, `403`, `404` |
| `POST /api/v1/claims/{claim_id}/register` | `CLAIM_UPDATE_ROLES` | `ClaimRegisterRequest` | `APIResponse[ClaimResponse]` | `200 OK`, `403`, `404`, `409` |
| `POST /api/v1/claims/{claim_id}/survey` | `CLAIM_UPDATE_ROLES` | `ClaimSurveyUpdateRequest` | `APIResponse[ClaimResponse]` | `200 OK`, `403`, `404`, `409`, `422` |
| `POST /api/v1/claims/{claim_id}/assess` | `CLAIM_UPDATE_ROLES` | `ClaimAssessmentRequest` | `APIResponse[ClaimResponse]` | `200 OK`, `403`, `404`, `409`, `422` |
| `POST /api/v1/claims/{claim_id}/approve` | `CLAIM_APPROVE_SETTLE_ROLES` | `ClaimApprovalRequest` | `APIResponse[ClaimResponse]` | `200 OK`, `403`, `404`, `409`, `422` |
| `POST /api/v1/claims/{claim_id}/settle` | `CLAIM_APPROVE_SETTLE_ROLES` | `ClaimSettlementRequest` | `APIResponse[ClaimResponse]` | `200 OK`, `403`, `404`, `409`, `422` |
| `POST /api/v1/claims/{claim_id}/close` | `CLAIM_APPROVE_SETTLE_ROLES` | `ClaimActionRemarksRequest` | `APIResponse[ClaimResponse]` | `200 OK`, `403`, `404`, `409` |
| `POST /api/v1/claims/{claim_id}/reject` | `CLAIM_APPROVE_SETTLE_ROLES` | `ClaimRejectionRequest` | `APIResponse[ClaimResponse]` | `200 OK`, `403`, `404`, `409`, `422` |
| `POST /api/v1/claims/{claim_id}/cancel` | `CLAIM_UPDATE_ROLES` | `ClaimActionRemarksRequest` | `APIResponse[ClaimResponse]` | `200 OK`, `403`, `404`, `409` |
| `POST /api/v1/claims/{claim_id}/reopen` | `CLAIM_APPROVE_SETTLE_ROLES` | `ClaimActionRemarksRequest` | `APIResponse[ClaimResponse]` | `200 OK`, `403`, `404`, `409` |
| `POST /api/v1/claims/{claim_id}/reverse-settlement` | `CLAIM_APPROVE_SETTLE_ROLES` | `ClaimActionRemarksRequest` | `APIResponse[ClaimResponse]` | `200 OK`, `403`, `404`, `409` |
| `POST /api/v1/claims/{claim_id}/documents` | `CLAIM_CREATE_ROLES` | `ClaimDocumentCreateRequest` | `APIResponse[ClaimDocumentResponse]` | `201 Created`, `403`, `404`, `422` |
| `GET /api/v1/claims/{claim_id}/documents` | `CLAIM_READ_ROLES` | Path: `claim_id` | `APIResponse[list[ClaimDocumentResponse]]` | `200 OK`, `403`, `404` |

---

## 3. Endorsement Endpoints (`/api/v1/endorsements`)

| Method & Path | Required Role Set | Request Schema | Response Schema | Status Codes |
|---|---|---|---|---|
| `POST /api/v1/endorsements/preview` | `ENDORSEMENT_CREATE_ROLES` | `EndorsementCreateRequest` | `APIResponse[EndorsementPreviewResponse]` | `200 OK`, `403`, `404`, `422` |
| `POST /api/v1/endorsements` | `ENDORSEMENT_CREATE_ROLES` | `EndorsementCreateRequest` | `APIResponse[EndorsementResponse]` | `201 Created` (`200 OK` on idempotent replay), `403`, `404`, `409`, `422` |
| `GET /api/v1/endorsements` | `ENDORSEMENT_READ_ROLES` | Query: `transaction_id`, `endorsement_status`, `endorsement_type`, `branch_id`, `agent_id`, `limit`, `offset` | `APIResponse[EndorsementListResponse]` | `200 OK`, `403` |
| `GET /api/v1/endorsements/{endorsement_id}` | `ENDORSEMENT_READ_ROLES` | Path: `endorsement_id` | `APIResponse[EndorsementResponse]` | `200 OK`, `403`, `404` |
| `POST /api/v1/endorsements/{endorsement_id}/submit` | `ENDORSEMENT_CREATE_ROLES` | `EndorsementActionRequest` | `APIResponse[EndorsementResponse]` | `200 OK`, `403`, `404`, `409` |
| `POST /api/v1/endorsements/{endorsement_id}/approve` | `ENDORSEMENT_APPROVE_APPLY_ROLES` | `EndorsementActionRequest` | `APIResponse[EndorsementResponse]` | `200 OK`, `403`, `404`, `409` |
| `POST /api/v1/endorsements/{endorsement_id}/apply` | `ENDORSEMENT_APPROVE_APPLY_ROLES` | `EndorsementApplyRequest` | `APIResponse[EndorsementResponse]` | `200 OK`, `403`, `404`, `409`, `422` |
| `POST /api/v1/endorsements/{endorsement_id}/reject` | `ENDORSEMENT_APPROVE_APPLY_ROLES` | `EndorsementRejectRequest` | `APIResponse[EndorsementResponse]` | `200 OK`, `403`, `404`, `409`, `422` |
| `POST /api/v1/endorsements/{endorsement_id}/cancel` | `ENDORSEMENT_CREATE_ROLES` | `EndorsementActionRequest` | `APIResponse[EndorsementResponse]` | `200 OK`, `403`, `404`, `409` |
| `POST /api/v1/endorsements/{endorsement_id}/reverse` | `ENDORSEMENT_APPROVE_APPLY_ROLES` | `EndorsementActionRequest` | `APIResponse[EndorsementResponse]` | `200 OK`, `403`, `404`, `409` |

---

## 4. Refund Endpoints (`/api/v1/refunds`)

| Method & Path | Required Role Set | Request Schema | Response Schema | Status Codes |
|---|---|---|---|---|
| `GET /api/v1/refunds` | `REFUND_APPROVE_WRITE_ROLES` | Query: `transaction_id`, `refund_status`, `branch_id` | `APIResponse[EndorsementListResponse]` | `200 OK`, `403` |
| `POST /api/v1/refunds/{endorsement_id}/approve` | `REFUND_APPROVE_WRITE_ROLES` | `RefundActionRequest` | `APIResponse[EndorsementResponse]` | `200 OK`, `403`, `404`, `409` |
| `POST /api/v1/refunds/{endorsement_id}/disburse` | `REFUND_APPROVE_WRITE_ROLES` | `RefundDisburseRequest` | `APIResponse[EndorsementResponse]` | `200 OK`, `403`, `404`, `409`, `422` |
| `POST /api/v1/refunds/{endorsement_id}/reverse` | `REFUND_APPROVE_WRITE_ROLES` | `RefundActionRequest` | `APIResponse[EndorsementResponse]` | `200 OK`, `403`, `404`, `409` |
