# Phase 12 — Search, Autocomplete & Typeahead Parity Matrix
## Exhaustive Mapping of 57 Legacy AJAX WebMethods (`SearchMethods.aspx.cs` & `AppSearchMethod.aspx.cs`) to FastAPI Endpoints

### 1. Architectural Overview
In the legacy C#/.NET 4.0 architecture (`InsurancefinalNew`), interactive search, typeahead autocomplete, duplicate checks, and operational dashboard counters were served by two ASP.NET AJAX code-behind files:
1. `SearchMethods.aspx.cs` (41 WebMethods): Main web portal search, autocomplete, duplicate checks, inward lookup, and operational status queries.
2. `AppSearchMethod.aspx.cs` (16 WebMethods): Mobile app / partner portal autocomplete, counter badge queries, and dashboard chart data feeds.

In the new FastAPI backend, these 57 legacy endpoints are unified under `/api/v1/search` with:
- **Strict JWT RBAC & Branch Scoping**: Eliminates legacy unauthenticated exposures and enforces branch/principal isolation.
- **Structured JSON Responses**: Replaces fragile legacy delimited strings (`"Name|Id"`, `"Model~Make"`, comma-separated values) with type-safe Pydantic models.
- **SQL Injection Safety**: Replaces legacy raw string concatenation with SQLAlchemy parameterized queries.
- **Backward-Compatible Query Support**: Provides dedicated endpoints for specialized search modes (e.g. cheque bounce search, inward search, duplicate checks).

---

### 2. Complete 57 WebMethod Parity Matrix

#### Part A: `SearchMethods.aspx.cs` (41 WebMethods)

| # | Legacy WebMethod | Legacy Delimiter / Return Format | FastAPI Endpoint | HTTP | Parameters / Query Semantics | RBAC / Scoping |
|---|---|---|---|---|---|---|
| 1 | `GetCustName` | `List<string>` (`"Name\|CustomerId"`) | `/api/v1/search/customers` | GET | `q`: search customer name prefix/contains (limit 20) | Branch-scoped |
| 2 | `GetCustVehicleNo` | `List<string>` (`"RegNo\|CustVehId"`) | `/api/v1/search/vehicles` | GET | `q`: search registration number (limit 20) | Branch-scoped |
| 3 | `GetCustEngNo` | `List<string>` (`"EngineNo\|CustVehId"`) | `/api/v1/search/vehicles` | GET | `q`: search engine number | Branch-scoped |
| 4 | `GetCustChassisNo` | `List<string>` (`"ChassisNo\|CustVehId"`) | `/api/v1/search/vehicles` | GET | `q`: search chassis number | Branch-scoped |
| 5 | `GetPolicyNo` | `List<string>` (`"PolicyNo\|TransanctionId"`) | `/api/v1/search/policies` | GET | `q`: search policy number, `search_type=all` | Branch-scoped |
| 6 | `GetChequePolicyNo` | `List<string>` (`"PolicyNo\|TransanctionId"`) | `/api/v1/search/policies` | GET | `q`: search policy number, `search_type=cheque` | Branch-scoped |
| 7 | `GetChqClearingPolicyNo` | `List<string>` (`"PolicyNo\|TransanctionId"`) | `/api/v1/search/policies` | GET | `q`: search policy number, `search_type=clearing` | Branch-scoped |
| 8 | `GetInwardNo` | `List<string>` (`"InwardNo\|TransanctionId"`) | `/api/v1/search/inward` | GET | `q`: search inward number prefix/contains | Branch-scoped |
| 9 | `GetAgentName` | `List<string>` (`"AgentName\|AgentId"`) | `/api/v1/search/autocomplete` | GET | `category=agent`, `q`: search agent name/code | Branch-scoped |
| 10 | `GetBranchName` | `List<string>` (`"BranchName\|BranchId"`) | `/api/v1/search/autocomplete` | GET | `category=branch`, `q`: search branch name/code | Branch-scoped |
| 11 | `GetMakeName` | `List<string>` (`"Make_Name\|Make_ID"`) | `/api/v1/search/autocomplete` | GET | `category=make`, `q`: search make name | Master / Global |
| 12 | `GetModelName` | `List<string>` (`"Model_Name\|Model_ID"`) | `/api/v1/search/autocomplete` | GET | `category=model`, `q`: search model name, `parent_id=make_id` | Master / Global |
| 13 | `GetBankName` | `List<string>` (`"BankName\|BankId"`) | `/api/v1/search/autocomplete` | GET | `category=bank`, `q`: search bank name | Master / Global |
| 14 | `GetRTOName` | `List<string>` (`"REG_code\|RTOId"`) | `/api/v1/search/autocomplete` | GET | `category=rto`, `q`: search RTO registration code/location | Master / Global |
| 15 | `GetInsuranceCompanyName`| `List<string>` (`"CompName\|Id"`) | `/api/v1/search/autocomplete` | GET | `category=insurer`, `q`: search insurer name/short code | Master / Global |
| 16 | `GetCustomerCode` | `List<string>` (`"CustomerCode\|Id"`) | `/api/v1/search/customers` | GET | `q`: search customer code | Branch-scoped |
| 17 | `GetCustomerMobile` | `List<string>` (`"MobileNo\|CustomerId"`) | `/api/v1/search/customers` | GET | `q`: search mobile number | Branch-scoped |
| 18 | `GetCustomerAadhar` | `List<string>` (`"AadharNo\|CustomerId"`) | `/api/v1/search/customers` | GET | `q`: search Aadhaar number | Branch-scoped |
| 19 | `GetCustomerPan` | `List<string>` (`"PanNo\|CustomerId"`) | `/api/v1/search/customers` | GET | `q`: search PAN number | Branch-scoped |
| 20 | `GetFranchiseName` | `List<string>` (`"Name\|FranchiseId"`) | `/api/v1/search/autocomplete` | GET | `category=franchise`, `q`: search franchise name/code | Branch-scoped |
| 21 | `GetEmployeeName` | `List<string>` (`"EmpName\|EmpId"`) | `/api/v1/search/autocomplete` | GET | `category=employee`, `q`: search employee name/code | Branch-scoped |
| 22 | `GetSurveyorName` | `List<string>` (`"SurveyorName\|Id"`) | `/api/v1/search/autocomplete` | GET | `category=surveyor`, `q`: search surveyor name | Branch-scoped |
| 23 | `GetGarageName` | `List<string>` (`"GarageName\|GarageId"`) | `/api/v1/search/autocomplete` | GET | `category=garage`, `q`: search workshop/garage name | Branch-scoped |
| 24 | `GetLedgerName` | `List<string>` (`"LedgerName\|LedgerId"`) | `/api/v1/search/autocomplete` | GET | `category=ledger`, `q`: search ledger account name | Financial / Branch |
| 25 | `CheckRegistrationNo` | `string` (`"EXISTS"` / `"AVAILABLE"`) | `/api/v1/search/quick-check/vehicle-no` | GET | `registration_no`, `financial_year`: duplicate check | Branch-scoped |
| 26 | `CheckEngineNo` | `string` (`"EXISTS"` / `"AVAILABLE"`) | `/api/v1/search/quick-check/engine-no` | GET | `engine_no`, `financial_year`: duplicate check | Branch-scoped |
| 27 | `CheckChassisNo` | `string` (`"EXISTS"` / `"AVAILABLE"`) | `/api/v1/search/quick-check/chassis-no` | GET | `chassis_no`, `financial_year`: duplicate check | Branch-scoped |
| 28 | `CheckPolicyNo` | `string` (`"EXISTS"` / `"AVAILABLE"`) | `/api/v1/search/quick-check/policy-no` | GET | `policy_no`: duplicate active policy check | Global / System |
| 29 | `CheckInwardNo` | `string` (`"EXISTS"` / `"AVAILABLE"`) | `/api/v1/search/quick-check/inward-no` | GET | `inward_no`: inward sequence collision check | Branch-scoped |
| 30 | `GetClaimNo` | `List<string>` (`"ClaimNo\|ClaimId"`) | `/api/v1/search/autocomplete` | GET | `category=claim`, `q`: search claim number | Branch-scoped |
| 31 | `GetEndorsementNo` | `List<string>` (`"EndorsementNo\|Id"`) | `/api/v1/search/autocomplete` | GET | `category=endorsement`, `q`: search endorsement number | Branch-scoped |
| 32 | `GetStateName` | `List<string>` (`"StateName\|StateID"`) | `/api/v1/search/autocomplete` | GET | `category=state`, `q`: search state name | Master / Global |
| 33 | `GetDistrictName` | `List<string>` (`"DistrictName\|DistrictID"`) | `/api/v1/search/autocomplete` | GET | `category=district`, `q`: search district name, `parent_id=state_id` | Master / Global |
| 34 | `GetCityName` | `List<string>` (`"CityName\|CityID"`) | `/api/v1/search/autocomplete` | GET | `category=city`, `q`: search city name | Master / Global |
| 35 | `GetPincode` | `List<string>` (`"Pincode\|PincodeId"`) | `/api/v1/search/autocomplete` | GET | `category=pincode`, `q`: search postal PIN code | Master / Global |
| 36 | `GetChequeNo` | `List<string>` (`"ChequeNo\|PaymentId"`) | `/api/v1/search/autocomplete` | GET | `category=cheque`, `q`: search cheque/instrument number | Branch-scoped |
| 37 | `GetVoucherNo` | `List<string>` (`"VoucherNo\|VoucherId"`) | `/api/v1/search/autocomplete` | GET | `category=voucher`, `q`: search voucher number | Financial / Branch |
| 38 | `GetEndorsementPolicyNo`| `List<string>` (`"PolicyNo\|TransId"`) | `/api/v1/search/policies` | GET | `q`: search policy eligible for endorsement | Branch-scoped |
| 39 | `GetClaimPolicyNo` | `List<string>` (`"PolicyNo\|TransId"`) | `/api/v1/search/policies` | GET | `q`: search active policy eligible for claim | Branch-scoped |
| 40 | `GetRenewalPolicyNo` | `List<string>` (`"PolicyNo\|TransId"`) | `/api/v1/search/policies` | GET | `q`: search expiring policy for renewal | Branch-scoped |
| 41 | `GetServerStatus` | `string` (`"ONLINE"`) | `/api/v1/search/server-status` | GET | Returns heartbeat status and UTC timestamp | Authenticated |

---

#### Part B: `AppSearchMethod.aspx.cs` (16 WebMethods)

| # | Legacy WebMethod | Legacy Return / Intent | FastAPI Endpoint | HTTP | Parameters / Semantics | RBAC / Scoping |
|---|---|---|---|---|---|---|
| 42 | `GetAppCustName` | Mobile customer autocomplete | `/api/v1/search/customers` | GET | Same as `GetCustName` with mobile app client flag | Agent / POSP Scoped |
| 43 | `GetAppCustVehicleNo` | Mobile vehicle registration autocomplete | `/api/v1/search/vehicles` | GET | Same as `GetCustVehicleNo` with mobile client flag | Agent / POSP Scoped |
| 44 | `GetAppMake` | Mobile make dropdown lookup | `/api/v1/search/autocomplete` | GET | `category=make`, `q` | Public / POSP |
| 45 | `GetAppModel` | Mobile model dropdown lookup | `/api/v1/search/autocomplete` | GET | `category=model`, `parent_id=make_id` | Public / POSP |
| 46 | `GetAppVariant` | Mobile variant dropdown lookup | `/api/v1/masters/variants` | GET | `model_id=model_id` | Public / POSP |
| 47 | `GetAppRTO` | Mobile RTO dropdown lookup | `/api/v1/masters/rtos` | GET | `search=q` | Public / POSP |
| 48 | `GetAppInsurer` | Mobile insurer dropdown lookup | `/api/v1/masters/insurance-companies` | GET | `search=q` | Public / POSP |
| 49 | `GetPendingEntryCount`| Operator inbox badge counter | `/api/v1/search/counters/pending` | GET | Counts pending inward/booking entries | Branch / Operator |
| 50 | `GetChequePendingCount`| Cheque clearance inbox counter | `/api/v1/search/counters/pending` | GET | Counts pending deposited cheques | Branch / Accounts |
| 51 | `GetEndorsementPendingCount`| Endorsement review counter | `/api/v1/search/counters/pending` | GET | Counts pending endorsement submissions | Branch / Operator |
| 52 | `GetClaimPendingCount`| Claim review inbox counter | `/api/v1/search/counters/pending` | GET | Counts pending claims awaiting survey/settlement | Claims Dept |
| 53 | `GetAppQuotationCount`| Mobile submitted quotes counter | `/api/v1/search/counters/pending` | GET | Counts active quotation requests | Agent / POSP |
| 54 | `GetAppPolicyCount` | Mobile booked policies counter | `/api/v1/search/counters/pending` | GET | Counts total booked policies | Agent / POSP |
| 55 | `GetDashboardPremiumChart`| Daily/Monthly premium bar chart data | `/api/v1/search/dashboard/summary`| GET | `chart_type=premium_summary`, period filter | Branch / Admin |
| 56 | `GetDashboardPolicyChart` | Policy count distribution pie chart | `/api/v1/search/dashboard/summary`| GET | `chart_type=policy_distribution`, period filter | Branch / Admin |
| 57 | `GetAppServerTime` | Legacy server time sync string | `/api/v1/search/server-status` | GET | Returns ISO 8601 server timestamp and timezone | Authenticated |

---

### 3. Delimiter Elimination & Serialization Standard
In the legacy backend, results were formatted as:
- Method `GetCustName`: `["RAMESH SHARMA|1001", "RAMESH PATEL|1002"]`
- Method `GetModelName`: `["ACTIVA 6G~12", "ACTIVA 125~13"]`
- Method `CheckRegistrationNo`: `"ALREADY_BOOKED_IN_FY"`

FastAPI standardizes these into typed JSON payloads:
```json
{
  "total": 2,
  "items": [
    {
      "id": 1001,
      "text": "RAMESH SHARMA",
      "extra": "MOB: 9876543210"
    },
    {
      "id": 1002,
      "text": "RAMESH PATEL",
      "extra": "MOB: 9822334455"
    }
  ]
}
```
For duplicate check endpoints:
```json
{
  "is_allowed": true,
  "message": "Vehicle registration number is available for booking.",
  "existing_id": null
}
```
This guarantees strict backward compatibility with modern frontend clients while preserving all business semantics of legacy validations.
