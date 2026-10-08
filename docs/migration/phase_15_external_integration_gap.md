# PHASE 15 — EXTERNAL INTEGRATION GAP AUDIT
## Reliable-Insurance-Backend: Post-Phase 14 Third-Party Integrations & Gateway Audit

---

### 1. Executive Summary
- **Phase 11 & 13 Integration Accomplishments**:
  - **Inbound PDF Parser Webhook (Phase 11)**: `POST /api/v1/documents/webhooks/policy-parser` with HMAC-SHA256 signature verification and structured staging (`tbl_calliber_policy_webhook`).
  - **Vehicle RC 3-Tier Cascade (Phase 13)**: Pluggable `VehicleRCProvider` (`MockVehicleRCProvider`, `SignzyProvider`, `APIClubProvider`) + 54-attribute local cache (`tbl_vehiclenorc_details`).
  - **Mobile OTP & Outbound SMS (Phase 13)**: Pluggable `SMSNotificationProvider` (`Fast2SMSProvider`, `IndiaTextProvider`) + SHA-256 salted OTP hash + `tbl_sms_log`.
  - **Push Notifications (Phase 13)**: Pluggable `PushNotificationProvider` (`OneSignalPushProvider`) + `tbl_messagemaster` & `tbl_messagedetails`.
  - **Email Dispatch (Phase 13)**: Pluggable `EmailNotificationProvider` (`SMTPEmailProvider`) + dynamic renewal Excel attachments.
- **Remaining Post-Phase 14 External Integrations**: **4 peripheral or legacy services** audited and classified.

---

### 2. External Integration Inventory & Status Matrix

| Integration Name | Legacy Usage & Reference | Modern Abstraction / Provider | Status | Priority | Safety / Production Invariant |
|---|---|---|---|:---:|---|
| **HiCaliber / Calliber Inbound Webhook** | `PolicyParserWebhook.aspx.cs` | `DocumentService` (`b11d0c5f1101`) | **MIGRATED (Phase 11)** | Completed | Optional HMAC-SHA256 (`X-Calliber-Signature`). |
| **Signzy / APIClub Vehicle RC** | `RC_CheckVehicleDtl.aspx.cs` | `IntegrationService` (`d13e0f7a1301`) | **MIGRATED (Phase 13)** | Completed | 3-tier cascade (`SYSTEM` $\rightarrow$ `CACHE` $\rightarrow$ `PROVIDER`). |
| **Fast2SMS / IndiaText Outbound SMS** | `App_Code/Send_SMS.cs` | `NotificationService` (`d13e0f7a1301`) | **MIGRATED (Phase 13)** | Completed | Configurable provider, rate limit, salt hash. |
| **OneSignal Mobile Push Notifications**| `SendPushNotiRenewal.aspx.cs` | `NotificationService` (`d13e0f7a1301`) | **MIGRATED (Phase 13)** | Completed | PlayerId registration and dual dispatch. |
| **SMTP Corporate Email Dispatch** | `SendMailToAutority.aspx.cs` | `NotificationService` (`d13e0f7a1301`) | **MIGRATED (Phase 13)** | Completed | Mock provider default in dev/test. |
| **External Payment Gateway Webhook** | Legacy manual UTR / gateway | `PaymentService` (`app/services/payment_service.py`) | **PRESERVED UNKNOWN (`GAP-UNK-003`)**| **P2** | Proprietary gateway callback spec unclosed without live provider docs. |
| **Google Maps Live Employee Tracking**| `Location.aspx.cs`, `GeoLocationClasses.cs` | None (Non-core ERP) | **DEFERRED** | **P3** | GPS coordinate logger. |
| **InsuranceAppService (External Quote)**| `http://103.76.188.138:85/Service.asmx` | `RatingEngineService` (Internal Engine)| **INTENTIONALLY OBSOLETE** | **P3** | Legacy external quote server; replaced by authoritative internal rating engine. |
| **Vantage POSP Broker Web Service** | `VantageTestingNewServer.aspx.cs` | None | **INTENTIONALLY OBSOLETE** | **P3** | Deprecated vendor broker server; no longer active. |

---

### 3. Deep-Dive on Remaining Items

#### 3.1 Payment Gateway Webhook Audit (`GAP-UNK-003`)
- **Legacy Evidence**: In the legacy ASP.NET application, online transactions in `InstaPay.aspx.cs` and `WalletTopup.aspx.cs` relied on external browser redirects to banking portals or manual UTR entry by accountants. No server-to-server webhook callback code or signature verification routines existed in C# source.
- **FastAPI Status**: Phase 8 implemented full ledger and wallet state machines with atomic unit-of-work boundaries (`AccTransId=10..14`). However, the exact webhook schema for external automated payment gateways (e.g. Razorpay, PayU, Cashfree) cannot be inferred from legacy code without external vendor specifications.
- **Audit Verdict**: `GAP-UNK-003` is strictly preserved. Zero webhook code should be fabricated without vendor API contracts.

#### 3.2 Obsolete External Web References
- **`InsuranceAppService`**: Points to a hardcoded legacy IP (`http://103.76.188.138:85/Service.asmx`). The legacy system occasionally forwarded policy parameters (`insertPolicy`) to this server. Phase 6 rating engine and Phase 7 policy booking perform all calculations natively, rendering this external service obsolete.
- **`VantageService`**: Experimental staging web reference for a third-party POSP distributor. No live traffic was processed through it. Classified as **Intentionally Obsolete**.
