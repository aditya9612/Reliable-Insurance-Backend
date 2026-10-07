# Repository Mapping Document — Phase 2

## 1. Overview
The repository layer provides clean, strongly-typed asynchronous data-access primitives across the 10 verified physical tables. It abstracts direct database queries away from upper application layers while strictly isolating data persistence from business rules.

Target Stack: Python 3.11+, SQLAlchemy 2.0 Async, `aiomysql`  
Directory: `app/repositories/`

---

## 2. Core Repository Principles & Non-Negotiables
1. **Data Access Only**: Repositories MUST NOT contain business rules, premium calculations, commission computations, tax adjustments, or workflow state transition rules.
2. **Asynchronous I/O**: Every query is executed asynchronously using `await session.execute(...)` or `await session.get(...)`.
3. **Session Lifecycle**: Repositories receive an active `AsyncSession` via constructor dependency injection and do not commit transactions directly, leaving transaction boundary control to callers/unit-of-work.
4. **Strong Typing**: Implemented using Python type hints, generic models (`BaseRepository[ModelType]`), and SQLAlchemy 2.0 `select()` statements.

---

## 3. Base Repository Primitives (`BaseRepository`)
File: [`app/repositories/base.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/app/repositories/base.py)

| Method | Signature | Description |
|---|---|---|
| `get_by_id` | `(id_val: Any) -> Optional[ModelType]` | Primary key lookup using `session.get()` |
| `list` | `(offset: int = 0, limit: int = 100) -> Sequence[ModelType]` | Paginated entity listing |
| `create` | `(instance: ModelType) -> ModelType` | Adds entity to session and flushes |
| `update` | `(instance: ModelType) -> ModelType` | Flushes dirty model state to session |
| `delete` | `(instance: ModelType) -> None` | Deletes entity and flushes |
| `count` | `() -> int` | Returns total row count via `func.count(PK)` |
| `exists` | `(id_val: Any) -> bool` | Checks existence of PK via `func.count(PK) > 0` |

---

## 4. Domain Repositories Catalog

### 4.1 CustomerRepository
File: [`app/repositories/customer.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/app/repositories/customer.py)  
Target Model: `Customer` (`tbl_customer`, PK `CustomerId`)
- `get_by_code(customer_code: str) -> Optional[Customer]`: Lookup by unique customer business code.
- `get_by_mobile(mobile_no: str) -> Sequence[Customer]`: Lookup by `MoblieNo1` or `MoblieNo2`.
- `get_by_pan(pan_no: str) -> Sequence[Customer]`: Lookup by PAN card number.
- `get_by_branch(branch_id: int) -> Sequence[Customer]`: Lookup all customers belonging to an office branch.

### 4.2 VehicleRepository
File: [`app/repositories/vehicle.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/app/repositories/vehicle.py)  
Target Model: `VehicleDetails` (`tbl_vehicledetails`, PK `CustVehId`)
- `get_by_registration_no(registration_no: str) -> Optional[VehicleDetails]`: Lookup by RTO registration number.
- `get_by_chassis_no(chassis_no: str) -> Optional[VehicleDetails]`: Lookup by vehicle chassis number (`ChaiseNo`).
- `get_by_customer_id(customer_id: int) -> Sequence[VehicleDetails]`: Lookup all vehicles registered to a customer.
- `get_by_engine_no(engine_no: str) -> Optional[VehicleDetails]`: Lookup by vehicle engine number.

### 4.3 TransactionRepository
File: [`app/repositories/transaction.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/app/repositories/transaction.py)  
Target Model: `Transaction` (`tbl_transaction`, PK `TransanctionId`)
- `get_by_policy_no(policy_no: str) -> Optional[Transaction]`: Lookup issued policy by `PolicyNo`.
- `get_by_inward_no(inward_no: str) -> Optional[Transaction]`: Lookup transaction record by `InwardNo`.
- `get_by_customer_id(customer_id: int) -> Sequence[Transaction]`: Lookup policies for a customer.
- `get_by_vehicle_id(cust_veh_id: int) -> Sequence[Transaction]`: Lookup policies for a vehicle asset.
- `get_by_status(status: str) -> Sequence[Transaction]`: Lookup policies by legacy `TStatus`.
- `get_by_agent_id(agent_id: int) -> Sequence[Transaction]`: Lookup policies booked under an agent.
- `get_by_branch_id(branch_id: int) -> Sequence[Transaction]`: Lookup policies issued under a branch.

### 4.4 TransactionAppRepository
File: [`app/repositories/transaction_app.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/app/repositories/transaction_app.py)  
Target Model: `TransactionAppNew` (`tbl_transactionappnew`, PK `TransId`)
- `get_by_user_id(user_id: int) -> Sequence[TransactionAppNew]`: Lookup proposals submitted by intake user.
- `get_by_contact_no(contact_no: str) -> Sequence[TransactionAppNew]`: Lookup proposals by phone number.
- `get_by_lead_no(lead_no: str) -> Optional[TransactionAppNew]`: Lookup intake proposal by `LeadNo`.
- `get_by_cash_status(cash_status: str) -> Sequence[TransactionAppNew]`: Lookup proposals by `CashStatus`.

### 4.5 PaymentRepository
File: [`app/repositories/payment.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/app/repositories/payment.py)  
Target Model: `TransactionPayment` (`tbl_transactionpayment`, PK `PaymentId`)
- `get_by_transaction_id(trans_id: int) -> Sequence[TransactionPayment]`: Lookup payment instruments linked to a policy transaction.
- `get_by_doc_no(doc_no: str) -> Sequence[TransactionPayment]`: Lookup cheque/draft instruments by `docno`.
- `get_by_branch_id(branch_id: int) -> Sequence[TransactionPayment]`: Lookup payments by branch.

### 4.6 AccountRepository
File: [`app/repositories/account.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/app/repositories/account.py)  
Target Model: `Account` (`tbl_account`, PK `AccountId`)
- `get_by_transaction_id(transaction_id: int) -> Sequence[Account]`: Lookup ledger journal lines for a transaction.
- `get_by_ledger_id(ledger_m_id: int) -> Sequence[Account]`: Lookup journal entries posted to a specific ledger head.
- `get_by_doc_no(doc_no: int) -> Sequence[Account]`: Lookup voucher journal lines by voucher `Doc_No`.
- `get_by_branch_id(branch_id: int) -> Sequence[Account]`: Lookup journal lines by branch.

### 4.7 LedgerRepository
File: [`app/repositories/ledger.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/app/repositories/ledger.py)  
Target Model: `LedgerMaster` (`tbl_ledgermaster`, PK `LedgerMId`)
- `get_by_name(ledger_name: str) -> Optional[LedgerMaster]`: Lookup chart of account head by name.
- `get_by_type(type_id: int) -> Sequence[LedgerMaster]`: Lookup ledger heads by `LedgerTypeId`.
- `get_by_group(group_id: int) -> Sequence[LedgerMaster]`: Lookup ledger heads by `LedgerGroupId`.
- `get_by_branch_id(branch_id: int) -> Sequence[LedgerMaster]`: Lookup branch-specific subledgers.

### 4.8 Commission Repositories
File: [`app/repositories/commission.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/app/repositories/commission.py)
- **`FranchiseCommissionRepository`** (`tbl_franchisecommission`, PK `FranchiseCommId`):
  - `get_by_transaction_id(trans_id: int)`: Lookup franchise commission entries by policy transaction.
  - `get_by_franchise_id(franchise_id: int)`: Lookup commissions booked for a franchise partner.
  - `get_by_agent_id(agent_id: int)`: Lookup commissions mapped to an agent.
- **`AgentCommissionRepository`** (`tbl_agentcommissionpayment`, PK `AgentCommId`):
  - `get_by_transaction_id(trans_id: int)`: Lookup POSP agent payment records by policy transaction.
  - `get_by_agent_name(agent_name: str)`: Lookup agent payment records by name.
  - `get_by_branch_name(branch_name: str)`: Lookup agent payment records by branch name.
- **`CutNPayCommissionRepository`** (`tbl_cutnpaycommpayable`, PK `CutNPayCommPayId`):
  - `get_by_transaction_id(trans_id: int)`: Lookup cut & pay deductions by transaction.
  - `get_by_policy_no(policy_no: str)`: Lookup cut & pay deductions by policy number.
  - `get_by_agent_id(agent_id: int)`: Lookup cut & pay deductions by agent ID.

---

## 5. Verification & Test Coverage
All repositories are validated through integration tests in [`tests/integration/test_repositories.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/tests/integration/test_repositories.py):
- Full CRUD execution on independent database `reliable_insurance_dev`
- Isolation safety check ensuring zero contact with `brahmainsurance`
- Rollback semantics check confirming uncommitted transactions do not persist
- Missing record handling returning `None` / empty lists cleanly
