# Phase 13 REST API Contract Specification
## Reliable-Insurance-Backend External Integrations, Notifications & Renewals

**Base URL**: `/api/v1`

---

### 1. Vehicle RC Integrations

#### `POST /api/v1/integrations/vehicle-rc/lookup`
- **Description**: 3-Tier cascade vehicle registration lookup (Internal DB -> Local Cache -> Vendor API).
- **Access**: `VEHICLE_RC_LOOKUP_ROLES` (`CUSTOMER_VEHICLE_READ_ROLES` excluding `CUSTOMER`).
- **Request Body**:
  ```json
  {
    "registration_number": "MH12AB1234",
    "force_refresh": false
  }
  ```
- **Response `200 OK`**:
  ```json
  {
    "source": "INTERNAL_SYSTEM" | "LOCAL_CACHE" | "EXTERNAL_PROVIDER",
    "data": {
      "request_id": "REQ-101",
      "license_plate_RegNo": "MH12AB1234",
      "owner_name": "JOHN DOE",
      "brand_name": "MARUTI SUZUKI",
      "brand_model": "SWIFT",
      "fuel_type": "PETROL",
      "chassis_number": "MA3E...",
      "engine_number": "K12M...",
      ...
    }
  }
  ```

---

### 2. Mobile OTP Authentication

#### `POST /api/v1/auth/otp/request`
- **Description**: Generates 6-digit cryptographic OTP, logs salted SHA-256 hash, dispatches via SMS.
- **Access**: Public / Unauthenticated.
- **Rate Limit**: 60s cooldown between requests per mobile number (configurable via `OTP_RESEND_COOLDOWN_SECONDS`). TTL = 5 minutes.
- **Request Body**:
  ```json
  {
    "mobile_number": "9850200000",
    "purpose": "LOGIN"
  }
  ```
- **Response `200 OK`**:
  ```json
  {
    "success": true,
    "message": "OTP sent successfully to 9850200000",
    "expires_in_seconds": 300
  }
  ```

#### `POST /api/v1/auth/otp/verify`
- **Description**: Verifies customer entered OTP against salted SHA-256 hash. Enforces 3 attempts limit.
- **Access**: Public / Unauthenticated.
- **Request Body**:
  ```json
  {
    "mobile_number": "9850200000",
    "otp_code": "123456",
    "purpose": "LOGIN"
  }
  ```
- **Response `200 OK`**:
  ```json
  {
    "verified": true,
    "access_token": "eyJhbGciOi...",
    "token_type": "bearer",
    "message": "OTP verification successful"
  }
  ```

---

### 3. Outbound Notifications

#### `POST /api/v1/notifications/sms/send`
- **Description**: Sends outbound SMS via configured provider and logs audit row in `tbl_sms_log`.
- **Access**: `NOTIFICATION_ADMIN_ROLES` (`GLOBAL_ADMIN_ROLES` + Managers/Heads).
- **Request Body**:
  ```json
  {
    "mobile_number": "9850200000",
    "message": "Your policy is due tomorrow.",
    "template_id": null
  }
  ```
- **Response `200 OK`**:
  ```json
  {
    "success": true,
    "provider": "MockSMSProvider",
    "message_id": "SMS-MOCK-abc123"
  }
  ```

#### `POST /api/v1/notifications/push/send`
- **Description**: Dispatches mobile push notification via OneSignal and dual-dispatches to internal inbox.
- **Access**: `NOTIFICATION_ADMIN_ROLES` (`GLOBAL_ADMIN_ROLES` + Managers/Heads).
- **Request Body**:
  ```json
  {
    "user_ids": ["admin", "telecaller1"],
    "title": "Renewal Notice",
    "message": "New policies require follow-up.",
    "notification_type": "RENEWAL"
  }
  ```
- **Response `200 OK`**:
  ```json
  {
    "success": true,
    "dispatched_count": 2,
    "provider_response_id": "PUSH-MOCK-uuid"
  }
  ```

#### `POST /api/v1/notifications/email/send-renewal-report`
- **Description**: Generates dynamic XML Excel renewal report and sends via SMTP.
- **Access**: `RENEWAL_EMAIL_ROLES` (`NOTIFICATION_ADMIN_ROLES` + Back Office, Operators, Calling staff).
- **Request Body**:
  ```json
  {
    "agent_id": 50,
    "month": 10,
    "year": "2024-2025",
    "recipient_email": "agent@reliable.com"
  }
  ```
- **Response `200 OK`**:
  ```json
  {
    "success": true,
    "recipient": "agent@reliable.com",
    "attachment_name": "Renewal_Report_2024-2025_10.xls"
  }
  ```

---

### 4. Policy Renewals & CRM

#### `GET /api/v1/renewals/due`
- **Description**: Retrieves expiring policies due for renewal. Scoped by user role/branch/tenancy.
- **Parameters**: `days_ahead` (default 30), `branch_id`, `agent_id`, `executive_id`, `skip`, `limit`.
- **Access**: Authenticated users (Agents see own, Execs see team, Admins see all).

#### `GET /api/v1/renewals/followups`
- **Description**: Lists active telecaller follow-up entries.
- **Parameters**: `financial_year`, `status`, `branch_id`, `skip`, `limit`.
- **Access**: `RENEWAL_TELECALLER_ROLES` (`ADMIN`, `OPERATOR`, `CLERK`, `TELECALLER`).

#### `POST /api/v1/renewals/followups`
- **Description**: Creates or reschedules telecaller follow-up remark and logs audit history.
- **Access**: `RENEWAL_TELECALLER_ROLES`.

#### `PUT /api/v1/renewals/{id}/status`
- **Description**: Transitions renewal status (`Follow` -> `Done`, `Lost`, `Vehicle`).
- **Access**: `RENEWAL_TELECALLER_ROLES`.

#### `GET /api/v1/renewals/dashboard`
- **Description**: Aggregates renewal CRM executive performance and company retention rate metrics.
- **Parameters**: `financial_year` (required), `month`, `branch_id`.
- **Access**: `RENEWAL_DASHBOARD_ROLES` (`GLOBAL_ADMIN_ROLES` + Heads, Managers, Employee Principals).
