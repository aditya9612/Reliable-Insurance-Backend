# Phase 13 — Target FastAPI Endpoint Inventory & Contracts

> **Audit Status**: COMPLETE (ALIGNED WITH LEGACY CODEBEHIND & FASTAPI SPECIFICATION)  
> **Phase**: Phase 13 (External Integrations, Notifications & Renewal) — Stage A  
> **Repository**: `Reliable-Insurance-Backend`  
> **Mode**: STRICTLY READ-ONLY (No endpoints mounted or code implemented)

---

## 1. Overview

This document defines the REST API endpoint inventory, request/response Pydantic schemas, HTTP status codes, and authentication requirements for Phase 13.

The endpoints are grouped into three core routers:
1. `/api/v1/integrations` (Vehicle RC & Provider lookups)
2. `/api/v1/notifications` (SMS, OTP, Push Notifications, SMTP Reports)
3. `/api/v1/renewals` (Expiring Policies, Telecaller CRM, Status Transitions, Management Dashboard)

---

## 2. API Endpoints Catalog

| # | HTTP Method | Endpoint URI | Router | Auth Required | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `POST` | `/api/v1/integrations/vehicle-rc/lookup` | Integrations | Bearer JWT | Queries vehicle RC via 3-tier cascade (System $\rightarrow$ Cache $\rightarrow$ External Provider). |
| 2 | `POST` | `/api/v1/auth/otp/request` | Auth / Notifications | Public | Generates and sends a 6-digit mobile OTP via SMS (`USP_UpdateOTP`, `LBR-002`). |
| 3 | `POST` | `/api/v1/auth/otp/verify` | Auth / Notifications | Public | Verifies submitted OTP against cached code; returns auth token on success. |
| 4 | `POST` | `/api/v1/notifications/sms/send` | Notifications | Admin / Manager | Dispatches transactional SMS via pluggable SMS gateway. |
| 5 | `POST` | `/api/v1/notifications/push/send` | Notifications | Admin / Manager | Dispatches targeted push notifications via OneSignal REST API. |
| 6 | `POST` | `/api/v1/notifications/email/send-renewal-report` | Notifications | Clerk / Manager | Generates renewal Excel spreadsheet and emails to assigned Agent/SE. |
| 7 | `GET` | `/api/v1/renewals/due` | Renewals | Authenticated | Lists policies nearing expiration within $N$ days (scoped by user role/branch). |
| 8 | `GET` | `/api/v1/renewals/followups` | Renewals | Telecaller / Clerk | Retrieves paginated active telecaller follow-up entries. |
| 9 | `POST` | `/api/v1/renewals/followups` | Renewals | Telecaller / Clerk | Records telecaller call remarks and reschedules next `followup_date`. |
| 10 | `PUT` | `/api/v1/renewals/{id}/status` | Renewals | Telecaller / Clerk | Transitions renewal record state (`FOLLOW_UP`, `RENEWED`, `LOST`, `VEHICLE_SOLD`). |
| 11 | `GET` | `/api/v1/renewals/dashboard` | Renewals | Manager / Admin | Aggregates summary renewal metrics, executive breakdown, and company distribution. |

---

## 3. Detailed Request & Response Schemas

### 3.1 Vehicle RC Lookup (`POST /api/v1/integrations/vehicle-rc/lookup`)
- **Request Body**:
  ```json
  {
    "registration_number": "MH12AB1234",
    "force_refresh": false
  }
  ```
- **Response Body (200 OK)**:
  ```json
  {
    "source": "LOCAL_CACHE",
    "registration_number": "MH12AB1234",
    "owner_name": "RAMESH SHARMA",
    "father_name": "SURESH SHARMA",
    "insurance_company": "ICICI LOMBARD",
    "insurance_policy": "3001/12345678/00/000",
    "insurance_expiry": "2025-04-15T00:00:00",
    "vehicle_class": "Motor Car (LMV)",
    "category": "4W",
    "registration_date": "2020-04-16T00:00:00",
    "chassis_number": "MA3E...1234",
    "engine_number": "K12M...5678",
    "fuel_type": "PETROL",
    "brand_name": "MARUTI SUZUKI",
    "brand_model": "SWIFT VXI",
    "cubic_capacity": "1197",
    "gross_weight": "1335",
    "rc_status": "ACTIVE",
    "created_at": "2026-10-07T12:00:00"
  }
  ```

### 3.2 Mobile OTP Lifecycle (`/api/v1/auth/otp/`)
- **Request OTP (`POST /api/v1/auth/otp/request`)**:
  ```json
  {
    "mobile_number": "9850266111",
    "purpose": "LOGIN"
  }
  ```
  *Response (200 OK)*:
  ```json
  {
    "success": true,
    "message": "OTP has been sent to 9850266111",
    "expires_in_seconds": 300
  }
  ```
- **Verify OTP (`POST /api/v1/auth/otp/verify`)**:
  ```json
  {
    "mobile_number": "9850266111",
    "otp_code": "482910",
    "purpose": "LOGIN"
  }
  ```
  *Response (200 OK)*:
  ```json
  {
    "verified": true,
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6...",
    "token_type": "bearer",
    "user_id": 142
  }
  ```

### 3.3 Push Notification (`POST /api/v1/notifications/push/send`)
- **Request Body**:
  ```json
  {
    "user_ids": ["AGT1024", "AGT1025"],
    "title": "Policy Renewal Alert",
    "message": "Customer Ramesh Sharma's policy for MH12AB1234 expires in 5 days.",
    "data": {
      "notification_type": "RENEWAL",
      "transaction_id": 45021
    }
  }
  ```
- **Response Body (200 OK)**:
  ```json
  {
    "success": true,
    "recipients_count": 2,
    "provider": "OneSignal",
    "external_id": "b18274a1-002f-4882-9982-fa82649b1102"
  }
  ```

### 3.4 Renewal Follow-up Interaction (`POST /api/v1/renewals/followups`)
- **Request Body**:
  ```json
  {
    "transaction_id": 45021,
    "registration_number": "MH12AB1234",
    "financial_year": "2024-2025",
    "remark": "Customer requested callback after 5 PM regarding NCB discount.",
    "followup_date": "2026-10-12T17:00:00",
    "insurance_company": "ICICI LOMBARD",
    "total_premium": 14850.00,
    "mobile_number": "9850266111"
  }
  ```
- **Response Body (201 Created)**:
  ```json
  {
    "id": 182,
    "transaction_id": 45021,
    "registration_number": "MH12AB1234",
    "financial_year": "2024-2025",
    "status": "FOLLOW_UP",
    "remark": "Customer requested callback after 5 PM regarding NCB discount.",
    "followup_date": "2026-10-12T17:00:00",
    "created_date": "2026-10-07T15:45:00",
    "is_deleted": 0
  }
  ```

### 3.5 Renewal Dashboard Metrics (`GET /api/v1/renewals/dashboard`)
- **Response Body (200 OK)**:
  ```json
  {
    "financial_year": "2024-2025",
    "month": 10,
    "summary": {
      "follow_up_count": 145,
      "renewed_done_count": 82,
      "lost_count": 14,
      "vehicle_sold_count": 5,
      "total_target_count": 246
    },
    "executive_breakdown": [
      {
        "executive_id": 12,
        "executive_name": "Sunil Patil",
        "follow_up_count": 45,
        "done_count": 28,
        "lost_count": 4,
        "vehicle_count": 1
      }
    ],
    "company_breakdown": [
      {
        "insurance_company": "ICICI LOMBARD",
        "due_count": 80,
        "renewed_count": 52,
        "retention_rate_pct": 65.0
      }
    ]
  }
  ```
