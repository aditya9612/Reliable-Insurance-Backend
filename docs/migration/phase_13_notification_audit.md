# Phase 13 — Notification Channels Legacy Audit (SMS, Push & SMTP)

> **Audit Status**: COMPLETE (CONFIRMED FROM C# CLIENT CODE & WEB SERVICES)  
> **Phase**: Phase 13 (External Integrations, Notifications & Renewal) — Stage A  
> **Repository**: `Reliable-Insurance-Backend`  
> **Legacy Source**: `InsurancefinalNew` (`Send_SMS.cs`, `SendPushNoti*.aspx.cs`, `SendMailToAutority.aspx.cs`, `adm_sendExcelTomailRenewal.aspx.cs`)  
> **Mode**: STRICTLY READ-ONLY (No external network traffic or provider calls initiated)

---

## 1. Executive Summary

Phase 13 Blocks B, C, and D encompass all outbound communication channels utilized by the legacy Reliable Assurance broker management system:
1. **Block B (SMS & Mobile OTP Gateway)**:
   - **IndiaText Gateway**: HTTP GET transactional API for transactional policy reminders and agent onboarding.
   - **Fast2SMS Gateway**: HTTP GET DLT-compliant API with pre-registered templates for payment receipts, employee notifications, and event triggers.
   - **Mobile OTP Engine**: POS/Agent mobile verification via `USP_UpdateOTP` (`LBR-002`, previously documented as `GAP-P5-002`).
2. **Block C (Push Notifications & Internal Messaging)**:
   - **OneSignal REST API**: Targeted push notifications delivered to mobile apps using `include_external_user_ids` (Agent/POSP usernames).
   - **Internal Message System**: Dual-dispatch to database inbox tables `tbl_messagemaster` and `tbl_messagedetails` (`Sp_MessageOperation`).
   - **Audit Feedback Loop**: Callbacks via `InsertPushNotiRenewal` calling `sp_InsertRenewalNotiStatus`.
3. **Block D (SMTP Email Engine)**:
   - **Gmail SMTP Relay**: `smtp.gmail.com:587` with TLS/SSL.
   - **Dynamic Attachments**: In-memory Excel generation (`ClosedXML` / HTML table export) and PDF rendering (`iTextSharp`).

---

## 2. Block B — SMS Gateways & OTP Lifecycle Audit

### 2.1 IndiaText Gateway Specification (`Insurance\Send_SMS.cs`)
- **Protocol**: HTTP GET via `System.Net.WebRequest`
- **Base URL**: `http://sms.indiatext.in/api/mt/SendSMS`
- **Query Parameters**:
  - `user`: `relass`
  - `password`: `[CREDENTIAL PRESENT — VALUE REDACTED]`
  - `senderid`: `RELIBL`
  - `channel`: `trans` (Transactional route)
  - `DCS`: `8` (Unicode/UTF-8) or `0` (Standard ASCII)
  - `flashsms`: `8` / `0`
  - `number`: Recipient 10-digit mobile number
  - `text`: URL-encoded message text
  - `route`: `01`
- **Legacy Error Handling**:
  ```csharp
  try {
      Stream objStream = wrGETURL.GetResponse().GetResponseStream();
      objReader = new StreamReader(objStream);
      objReader.Close();
  } catch (Exception ex) {
      ex.ToString(); // SILENT SWALLOW — NO RETRY, NO DB AUDIT LOG
  }
  ```
- **FastAPI Modernization Requirement**:
  - Outbox pattern or Celery async task (`send_sms_task`).
  - Structured DB logging (`tbl_sms_log`) capturing status code, timestamp, recipient, and provider response.

### 2.2 Fast2SMS Gateway Specification (`POSP_MultiEntryIdealPayment.aspx.cs`, `ShowEventCalender.aspx.cs`)
- **Protocol**: HTTPS GET via `WebRequest`
- **Base URL**: `https://www.fast2sms.com/dev/bulkV2`
- **DLT Compliance**: Built-in India Telecom Regulatory Authority (TRAI) Distributed Ledger Technology (DLT) compliance.
- **Query Parameters**:
  - `authorization`: `[CREDENTIAL PRESENT — VALUE REDACTED]`
  - `route`: `dlt`
  - `sender_id`: `relast`
  - `message`: DLT Template ID (Numeric)
  - `variables_values`: Pipe-delimited parameter values (e.g., `UserName|Amount|`)
  - `flash`: `0`
  - `numbers`: Recipient mobile number
- **Confirmed DLT Templates in Code**:
  - Template `131146`: POSP payment notification (Legacy)
  - Template `150014`: Agent commission transfer notification:
    `"Dear {1}, Your payment Rs. {2} has been Transfer to your account"`
  - Template `160987`: Event / Credential notification:
    `"{username}|{password}|{code}|"`

### 2.3 Mobile OTP Lifecycle (`USP_UpdateOTP`, `LBR-002`)
- **Legacy Flow**:
  - POS / Agent requests login via mobile.
  - Legacy `Service.asmx.cs` issues OTP and calls `USP_UpdateOTP(UserId, OTP, "GENERATE")`.
  - Dispatches OTP via `Send_SMS.cs`.
  - Agent submits OTP; verified via `USP_UpdateOTP(UserId, OTP, "VERIFY")`.
- **FastAPI Gap Remediation (`GAP-P5-002`)**:
  - Redis / DB-backed OTP lifecycle with 5-minute TTL.
  - Maximum 3 verification attempts before invalidation.
  - Cryptographic hashing (SHA-256) of OTP before persistence.
  - Pluggable `SMSProvider` (`MockSMSProvider` in test/dev, `Fast2SMS` / `IndiaText` in production).

---

## 3. Block C — Push Notifications (OneSignal) & Internal Messaging

### 3.1 OneSignal Architecture & Payload Schema
- **Endpoint**: `https://onesignal.com/api/v1/notifications`
- **HTTP Method**: `POST`
- **Headers**:
  - `Content-Type: application/json`
  - `Authorization: Basic [CREDENTIAL PRESENT — VALUE REDACTED]`
- **Payload Structure**:
  ```json
  {
    "app_id": "0285748c-7ffb-41b6-a656-bce336f73330",
    "include_external_user_ids": ["<external_user_id>"],
    "headings": {
      "en": "<Notification Title>"
    },
    "contents": {
      "en": "<Notification Message>"
    },
    "data": {
      "app_name": "Reliable Assurance"
    }
  }
  ```
- **Legacy Vulnerability**:
  - In `SendPushNotiRenewal.aspx` and `PolicyNoUpdatePushNoti.aspx`, the OneSignal REST API key was hardcoded in **client-side browser JavaScript**, exposing full notification sending capabilities to anyone inspecting the page source.
  - **FastAPI Remediation**: Strict server-side dispatch via `httpx.AsyncClient` inside a secured background service (`PushNotificationService`).

### 3.2 Targeting & Audience Segmentation
Targeting uses `include_external_user_ids` mapped to user principal IDs:
- **Agents**: Agent username / code retrieved via `BLL_Message.BLL_getAgentUserNameByUserId(AgentId, "AGT")`.
- **Franchisees**: Franchise username retrieved via `BLL_getAgentUserNameByUserId(FrId, "FR")`.
- **Sales Executives / Employees**: Employee code via `BLL_getAgentUserNameByUserId(EmpId, "EMP")`.

### 3.3 Confirmed Push Notification Triggers in Legacy

| Trigger Type | Source File (`File:Line`) | Notification Title | Message Template | Recipient Scope |
| :--- | :--- | :--- | :--- | :--- |
| **Renewal Expiry Alert** | `SendPushNotiRenewal.aspx.cs:L59` | `Policy Renewal` | `"Dear Partner Your customer {Name} Vehicle no {RegNo} Insurance Policy has Expiring on {ExpiryDate}. Kindly contact our office -9850266111. Thanks- Reliable Assurance."` | Assigned Agent / POSP |
| **Birthday Wish** | `SendPushNotiForBdayWish.aspx.cs:L55` | `Birthday Wish` | `"Happy Birthday Dear Partner {Name} ! We hope your special day is as fantastic as you are. Thanks- Reliable Assurance."` | Agent / Employee on birthday |
| **Policy Booked / Generated** | `PolicyNoUpdatePushNoti.aspx.cs:L3011` | `Policy Update` | `"For {RegNo} Policy is Generated Please Check."` | Originating Agent / Branch |
| **Payment Credited** | `POSP_MultiEntryIdealPayment.aspx.cs:L455` | `Payment Update` | Payment transfer confirmation | Paid Agent / POSP |

### 3.4 Dual Dispatch: Internal Inbox (`tbl_messagemaster` & `tbl_messagedetails`)
Whenever a push notification is sent, legacy also records an internal notification into broker user inboxes:
1. `sp_InsertMessageMaster`: Inserts text into `tbl_messagemaster`, returns `P_msgid`.
2. `Sp_MessageOperation`: Inserts row into `tbl_messagedetails` with:
   - `P_Id`: `P_msgid`
   - `P_userId`: Target User ID
   - `P_Messagedate`: Current timestamp
   - `P_readStatus`: `0` (Unread)
   - `P_Flag`: `"PR"` (Policy Renewal) or `"PM"` (Payment / Multi-entry)
   - `P_Opr`: `"Insert"`

---

## 4. Block D — SMTP Email Engine Audit

### 4.1 SMTP Server Configuration
- **Host**: `smtp.gmail.com`
- **Port**: `587`
- **SSL/TLS**: `EnableSsl = true` (`STARTTLS`)
- **Sender Address**: `reliable.mis1@gmail.com`
- **Authentication**: Dedicated Google App Password (`16-character token`, redacted).

### 4.2 Use Cases & Document Generation

#### 1. Commission Statement & Renewal Excel Dispatch (`adm_sendExcelTomailRenewal.aspx.cs`)
- **Recipient**: Target Agent / POSP and CC Sales Executive (`SE_EmailId`).
- **Subject**: `"Renewal Report - {Month} {FinancialYear}"` / `"Commission Statement - {Month} {FinancialYear}"`.
- **Body**: Standardized blue-themed HTML table with broker contact information (`9822166111`).
- **Attachment**: In-memory Excel workbook generated from GridView using `ClosedXML` / UTF-8 HTML table stream (`MemoryStream` with MIME type `application/vnd.ms-excel`).

#### 2. Daily Management InstaPay Report (`SendMailToAutority.aspx.cs`)
- **Recipient**: Broker executive management / authorities.
- **Trigger**: Automated / manual daily run.
- **Query**: `sp_InstapayReport(0, Now, Now, "NEWSUMMERY")`.
- **Body & Attachment**: Renders PDF summary using `iTextSharp` detailing agent collections, bank UTRs, and net premiums.

---

## 5. Security & Isolation Hardening Summary

| Dimension | Legacy WebForms Vulnerability | FastAPI Production-Hardened Architecture |
| :--- | :--- | :--- |
| **API Keys** | Hardcoded in `.aspx.cs` and `.aspx` client JS. | Configured via environment variables; never exposed in client bundles. |
| **Provider Isolation** | Direct synchronous HTTP calls to vendors in request thread. | Abstract provider interfaces (`SMSProvider`, `PushProvider`, `EmailProvider`) with `Mock*` defaults for dev/test. |
| **Error Resilience** | Silent `catch (Exception ex) { ex.ToString(); }`. | Explicit error logging, status code propagation, and DB audit logging. |
| **Outbox / Background** | Synchronous blocking calls delaying UI page render. | Non-blocking Celery tasks or async HTTP client calls (`httpx.AsyncClient`). |
