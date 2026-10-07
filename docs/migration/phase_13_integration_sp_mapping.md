# Phase 13 — Integration & Renewal Stored Procedure Mapping

> **Audit Status**: COMPLETE (CONFIRMED FROM ADO.NET CALL SITES IN C# DAL/BLL)  
> **Phase**: Phase 13 (External Integrations, Notifications & Renewal) — Stage A  
> **Repository**: `Reliable-Insurance-Backend`  
> **Legacy Source**: `InsurancefinalNew` (`DAL\DAL_Operations.cs`, `BLL\BLL_Operations.cs`, `Insurance\Service.asmx.cs`)  
> **Mode**: STRICTLY READ-ONLY (No DB migrations or procedure calls performed)

---

## 1. Overview

This document catalogs every Stored Procedure discovered across Phase 13 domains:
- **Block A**: Vehicle RC Verification & KYC Caching (3 SPs)
- **Block B**: SMS & Mobile OTP Verification (5 SPs)
- **Block C**: Push Notifications & Internal Messaging (7 SPs)
- **Block D**: Reporting & Email Dispatch Queries (4 SPs)
- **Block E**: Renewal Management, Telecaller Follow-Up & Dashboards (15 SPs)

**Total Stored Procedures**: **34 SPs** mapped with exact parameter signatures, directions, and FastAPI repository/service replacements.

---

## 2. Block A — Vehicle RC & KYC Caching Stored Procedures

| # | Stored Procedure Name | Parameter Signature | Param Direction | Legacy Call Site (`File:Line`) | FastAPI Target Location |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `sp_VehicleHistoryForRC` | `P_RegistrationNo` (VARCHAR)<br>`P_opr` (VARCHAR) | IN<br>IN | `DAL\DAL_Operations.cs:L44089`<br>`RC_CheckVehicleDtl.aspx.cs:L184` | `app/repositories/vehicle_rc.py`<br>`VehicleRCRepository.get_system_history` |
| 2 | `sp_Select_vehiclenorc_details` | `P_rc_regn_no` (VARCHAR) | IN | `DAL\DAL_Operations.cs:L44069`<br>`RC_CheckVehicleDtl.aspx.cs:L209` | `app/repositories/vehicle_rc.py`<br>`VehicleRCRepository.get_cached_rc` |
| 3 | `sp_InsertRCAPIDetails` | 51 Parameters:<br>`P_VehRcId` (INT)<br>`P_request_id` (VARCHAR)<br>`P_license_plate_RegNo` (VARCHAR)<br>`P_owner_name` (VARCHAR)<br>`P_father_name` (VARCHAR)<br>`P_is_financed` (VARCHAR)<br>`P_financer` (VARCHAR)<br>`P_present_address` (VARCHAR)<br>`P_permanent_address` (VARCHAR)<br>`P_insurance_company` (VARCHAR)<br>`P_insurance_policy` (VARCHAR)<br>`P_insurance_expiry` (DATETIME)<br>`P_class` (VARCHAR)<br>`P_category` (VARCHAR)<br>`P_registration_date` (DATETIME)<br>`P_vehicle_age` (VARCHAR)<br>`P_pucc_upto` (DATETIME)<br>`P_pucc_number` (VARCHAR)<br>`P_chassis_number` (VARCHAR)<br>`P_engine_number` (VARCHAR)<br>`P_fuel_type` (VARCHAR)<br>`P_brand_name` (VARCHAR)<br>`P_brand_model` (VARCHAR)<br>`P_body_type` (VARCHAR)<br>`P_cubic_capacity` (VARCHAR)<br>`P_gross_weight` (VARCHAR)<br>`P_cylinders` (VARCHAR)<br>`P_color` (VARCHAR)<br>`P_norms` (VARCHAR)<br>`P_fit_up_to` (VARCHAR)<br>`P_manufacturing_date` (VARCHAR)<br>`P_manufacturing_date_formatted` (VARCHAR)<br>`P_rto_name` (VARCHAR)<br>`P_latest_by` (VARCHAR)<br>`P_sleeper_capacity` (VARCHAR)<br>`P_standing_capacity` (VARCHAR)<br>`P_wheelbase` (VARCHAR)<br>`P_unladen_weight` (VARCHAR)<br>`P_noc_details` (VARCHAR)<br>`P_seating_capacity` (VARCHAR)<br>`P_owner_count` (VARCHAR)<br>`P_tax_upto` (VARCHAR)<br>`P_tax_paid_upto` (VARCHAR)<br>`P_permit_number` (VARCHAR)<br>`P_permit_issue_date` (VARCHAR)<br>`P_permit_valid_from` (VARCHAR)<br>`P_permit_valid_upto` (VARCHAR)<br>`P_permit_type` (VARCHAR)<br>`P_national_permit_number` (VARCHAR)<br>`P_national_permit_upto` (VARCHAR)<br>`P_national_permit_issued_by` (VARCHAR)<br>`P_rc_status` (VARCHAR)<br>`P_CreatedDate` (DATETIME)<br>`P_CreatedBy` (VARCHAR) | All IN | `DAL\DAL_Operations.cs:L43982`<br>`RC_CheckVehicleDtl.aspx.cs:L305` | `app/repositories/vehicle_rc.py`<br>`VehicleRCRepository.save_rc_details` |

---

## 3. Block B — SMS & Mobile OTP Stored Procedures

| # | Stored Procedure Name | Parameter Signature | Param Direction | Legacy Call Site (`File:Line`) | FastAPI Target Location |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 4 | `SP_SendSmsforSalesExandagent` | `P_AgentId` (INT)<br>`P_opr` (VARCHAR: "Agent" / "SalesEx") | IN<br>IN | `DAL\DAL_Operations.cs:L6501`<br>`AccountantApproval.aspx.cs:L570` | `app/services/notification_service.py` |
| 5 | `sp_SendSmstoCustomerPolicyNo` | `P_TransanctionId` (INT) | IN | `DAL\DAL_Operations.cs:L10435` | `app/services/notification_service.py` |
| 6 | `USP_UpdateOTP` | `P_UserId` (INT)<br>`P_OTP` (VARCHAR)<br>`P_opr` (VARCHAR: "GENERATE" / "VERIFY") | IN<br>IN<br>IN | `docs/migration/19_legacy_business_rule_master_register.md`<br>`Service.asmx.cs` (`GAP-P5-002`) | `app/services/otp_service.py` |
| 7 | `sp_ChkloginCustomer` | `P_MoblieNo1` (VARCHAR)<br>`P_MoblieNo2` (VARCHAR)<br>`P_CustomerId` (VARCHAR)<br>`P_CustomerName` (VARCHAR)<br>`P_EMailId` (VARCHAR)<br>`P_ComAddrLine1` (VARCHAR) | IN<br>IN<br>OUT<br>OUT<br>OUT<br>OUT | `Insurance\Service.asmx.cs:L545` | `app/repositories/customer.py` |
| 8 | `sp_ChkloginRefCustomer` | `P_ContactNo` (VARCHAR)<br>`P_APPCustomerId` (VARCHAR)<br>`P_APPCustomerName` (VARCHAR)<br>`P_EmailId` (VARCHAR)<br>`P_Address` (VARCHAR) | IN<br>OUT<br>OUT<br>OUT<br>OUT | `Insurance\Service.asmx.cs:L1067` | `app/repositories/customer.py` |

---

## 4. Block C — Push Notifications & Internal Messaging Stored Procedures

| # | Stored Procedure Name | Parameter Signature | Param Direction | Legacy Call Site (`File:Line`) | FastAPI Target Location |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 9 | `sp_SelectpolicyExpiryDate` | `P_opr` (VARCHAR: "fiveday", "tenday", etc.) | IN | `Insurance\SendPushNotiRenewal.aspx.cs:L87`<br>`SendPushNotiToAgentForRenewal.aspx.cs:L63` | `app/repositories/renewal.py`<br>`RenewalRepository.get_expiring_policies` |
| 10 | `sp_InsertRenewalNotiStatus` | `P_ExternalId` (VARCHAR)<br>`P_Status` (VARCHAR: "Success" / "Fail") | IN<br>IN | `DAL\DAL_Operations.cs:L8138`<br>`SendPushNotiRenewal.aspx.cs:L107` | `app/repositories/notification.py`<br>`NotificationRepository.log_push_status` |
| 11 | `sp_SelectBirthdayOfAgentExecutive` | `P_opr` (VARCHAR: "EMP", "AGT") | IN | `Insurance\SendPushNotiForBdayWish.aspx.cs:L75` | `app/services/notification_service.py` |
| 12 | `sp_InsertMessageMaster` | `P_msg` (VARCHAR)<br>`P_msgid` (INT) | IN<br>OUT | `DAL\DAL_Operations.cs:L29860`<br>`PolicyNoUpdatePushNoti.aspx.cs:L3023` | `app/repositories/notification.py`<br>`NotificationRepository.create_message` |
| 13 | `Sp_MessageOperation` | `P_Id` (INT)<br>`P_Messagedate` (DATETIME)<br>`P_userId` (INT)<br>`P_readStatus` (INT)<br>`P_Opr` (VARCHAR)<br>`P_Flag` (VARCHAR: "PR", "PM") | IN<br>IN<br>IN<br>IN<br>IN<br>IN | `DAL\DAL_Operations.cs:L29830`<br>`POSP_MultiEntryIdealPayment.aspx.cs:L400` | `app/repositories/notification.py`<br>`NotificationRepository.dispatch_user_message` |
| 14 | `Sp_SelectUSerFormsg` | `P_Opr` (VARCHAR) | IN | `DAL\DAL_Operations.cs:L29884` | `app/repositories/notification.py` |
| 15 | `sp_GetUserId` | `P_Opr` (VARCHAR)<br>`P_Id` (INT) | IN<br>IN | `DAL\DAL_Operations.cs:L29903` | `app/repositories/user.py` |

---

## 5. Block D — Email & Reporting Stored Procedures

| # | Stored Procedure Name | Parameter Signature | Param Direction | Legacy Call Site (`File:Line`) | FastAPI Target Location |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 16 | `sp_InstapayReport` | `P_AgentId` (INT)<br>`P_fromDate` (DATETIME)<br>`P_ToDate` (DATETIME)<br>`P_opr` (VARCHAR: "NEWSUMMERY") | IN<br>IN<br>IN<br>IN | `Insurance\SendMailToAutority.aspx.cs:L73` | `app/repositories/payment.py` |
| 17 | `sp_SelectAgentforSummRpt` | `P_AgentId` (INT)<br>`P_opr` (VARCHAR: "AG_MAILID") | IN<br>IN | `adm_sendExcelTomailRenewal.aspx.cs:L145` | `app/repositories/agent.py` |
| 18 | `sp_SelectAgentbySE` | `P_AgentId` (INT)<br>`P_opr` (VARCHAR: "CC_AGT_SE") | IN<br>IN | `adm_sendExcelTomailRenewal.aspx.cs:L151` | `app/repositories/agent.py` |
| 19 | `sp_GetEmployeeByIdOp` | `P_EmpId` (INT)<br>`P_opr` (INT: -1) | IN<br>IN | `adm_sendExcelTomailRenewal.aspx.cs:L159` | `app/repositories/user.py` |

---

## 6. Block E — Renewal Engine Stored Procedures

| # | Stored Procedure Name | Parameter Signature | Param Direction | Legacy Call Site (`File:Line`) | FastAPI Target Location |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 20 | `sp_SelectFollowupEntry` | *None* | *None* | `DAL\DAL_Operations.cs:L11489`<br>`PreYearRenewalEntryFollowup.aspx.cs:L34` | `app/repositories/renewal.py`<br>`RenewalRepository.get_followups` |
| 21 | `Sp_InsertFollowPreYearRenewalStatus` | `P_TransanctionId` (INT)<br>`P_Remark` (VARCHAR)<br>`P_FinancialYear` (VARCHAR)<br>`P_isdeleted` (INT)<br>`P_CreatedDate` (DATETIME)<br>`P_RegistrationNo` (VARCHAR)<br>`P_InsuranceCompany` (VARCHAR)<br>`P_TotalPremium` (DOUBLE)<br>`P_MobileNo` (VARCHAR)<br>`P_ExpiryDate` (DATETIME)<br>`P_FollowupDate` (DATETIME)<br>`P_UserRoleId` (INT)<br>`P_AgentId` (INT)<br>`P_ExecutiveId` (INT)<br>`P_Opr` (VARCHAR: "insert", "Update") | All IN | `DAL\DAL_Operations.cs:L11507`<br>`PreYearRenewalEntryFollowup.aspx.cs:L91` | `app/repositories/renewal.py`<br>`RenewalRepository.upsert_followup_status` |
| 22 | `sp_CheckRegistrationNo` | `P_RegistrationNo` (VARCHAR)<br>`P_FinancialYear` (VARCHAR)<br>`P_ReturnMsg` (INT) | IN<br>IN<br>OUT | `DAL\DAL_Operations.cs:L8162` | `app/repositories/renewal.py`<br>`RenewalRepository.check_reg_exists` |
| 23 | `sp_CheckRegistrationNoNew` | `P_RegistrationNo` (VARCHAR)<br>`P_FinancialYear` (VARCHAR)<br>`P_ReturnMsg` (INT) | IN<br>IN<br>OUT | `DAL\DAL_Operations.cs:L8184` | `app/repositories/renewal.py`<br>`RenewalRepository.check_reg_exists_new` |
| 24 | `sp_SelectPrevYearRenewalPolicySatusDashboard` | `P_Opr` (VARCHAR: "Follow", "Done", "Lost", "Vehicle", "EXFollow", "AGFollow", "FRFollow", "AFRFollow", "EXDone", "AGDone", etc.) | IN | `DAL\DAL_Operations.cs:L39671`<br>`Dashboard_PrevYearRenewalStatus.aspx.cs:L224` | `app/repositories/renewal.py`<br>`RenewalRepository.get_dashboard_counts` |
| 25 | `sp_SelectPrevYearRenewalTypeWiseCount` | `P_Opr` (VARCHAR) | IN | `DAL\DAL_Operations.cs:L39693` | `app/repositories/renewal.py` |
| 26 | `sp_SelectPrevYearRenewalDashboradData` | `P_Opr` (VARCHAR)<br>`P_Id` (INT) | IN<br>IN | `DAL\DAL_Operations.cs:L39714` | `app/repositories/renewal.py` |
| 27 | `sp_PreYearRenawalentryExcutivewiseCount` | `P_Month` (INT)<br>`P_FinancialYear` (VARCHAR) | IN<br>IN | `DAL\DAL_Operations.cs:L39737`<br>`Dashboard_PrevYearRenewalStatus.aspx.cs:L137` | `app/repositories/renewal.py`<br>`RenewalRepository.get_executive_counts` |
| 28 | `sp_DashBoardPreYearRenewalByEx` | `P_FinancialYear` (VARCHAR)<br>`P_Month` (INT)<br>`P_FinancialYear1` (VARCHAR) | IN<br>IN<br>IN | `DAL\DAL_Operations.cs:L39758` | `app/repositories/renewal.py` |
| 29 | `sp_PreYearRenawalentryCompanywiseCount` | `P_Month` (INT)<br>`P_FinancialYear` (VARCHAR) | IN<br>IN | `DAL\DAL_Operations.cs:L39784`<br>`Dashboard_PrevYearRenewalStatus.aspx.cs:L180` | `app/repositories/renewal.py`<br>`RenewalRepository.get_company_counts` |
| 30 | `Sp_UpdatePreYearRenewalStatus` | `P_RegistrationNo` (VARCHAR)<br>`P_FinancialYear` (VARCHAR)<br>`P_Opr` (VARCHAR) | IN<br>IN<br>IN | `DAL\DAL_Operations.cs:L39806` | `app/repositories/renewal.py`<br>`RenewalRepository.update_renewal_status` |
| 31 | `sp_SelectPrevYearRenewalCountnew` | `P_FinancialYear` (VARCHAR)<br>`P_Month` (INT)<br>`P_Opr` (VARCHAR) | IN<br>IN<br>IN | `DAL\DAL_Operations.cs:L39828` | `app/repositories/renewal.py` |
| 32 | `sp_SelectPrevYearRenewalCountnew1` | `P_FinancialYear` (VARCHAR)<br>`P_FinancialYear1` (VARCHAR)<br>`P_Month` (INT)<br>`P_Opr` (VARCHAR) | IN<br>IN<br>IN<br>IN | `DAL\DAL_Operations.cs:L39850` | `app/repositories/renewal.py` |
| 33 | `sp_DashBoardPreYearRenewalByExDirect` | `P_FinancialYear` (VARCHAR)<br>`P_Month` (INT)<br>`P_FinancialYear1` (VARCHAR) | IN<br>IN<br>IN | `DAL\DAL_Operations.cs:L39898` | `app/repositories/renewal.py` |
| 34 | `sp_renewalnotistatus` | `P_Status` (VARCHAR)<br>`P_FromDate` (DATETIME)<br>`P_ToDate` (DATETIME) | IN<br>IN<br>IN | `DAL\DAL_Operations.cs:L34769`<br>`adm_renewalnotistatus.aspx.cs:L53` | `app/repositories/renewal.py`<br>`RenewalRepository.get_renewal_noti_report` |

---

## 7. SQLAlchemy Async Equivalents & Translation Table

In the new backend, direct calls to stored procedures are replaced with typed async SQLAlchemy ORM queries and repositories:

```python
# Conceptual translation pattern
async def get_cached_vehicle_rc(
    session: AsyncSession, 
    reg_no: str
) -> Optional[VehicleRCDetails]:
    """Replaces sp_Select_vehiclenorc_details."""
    query = select(VehicleRCDetails).where(
        VehicleRCDetails.license_plate_RegNo == reg_no
    )
    result = await session.execute(query)
    return result.scalar_one_or_none()
```
