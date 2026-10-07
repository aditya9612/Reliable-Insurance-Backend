# Phase 12 — API Contract Specification
## Master Data, Underwriting Lookups, Organizational Masters & Search / Autocomplete

### 1. Base URL & Common Conventions
- Base Path: `/api/v1`
- Authentication: Bearer JWT Token via `Authorization: Bearer <token>` header
- Standard Error Responses:
  - `401 Unauthorized`: Missing or invalid JWT
  - `403 Forbidden`: Authenticated user lacks required role or branch privilege
  - `404 Not Found`: Requested master entity does not exist or is marked deleted
  - `422 Unprocessable Entity`: Schema validation error

---

### 2. Block 1: Vehicle Masters, RTO & Insurer Endpoints (`/api/v1/masters`)

#### 1. Vehicle Types
- **`GET /api/v1/masters/vehicle-types`**
  - **Query Params**: `skip` (int, default 0), `limit` (int, default 100), `app_quotation_only` (bool, default False)
  - **Response (200)**: `List[VehicleTypeResponse]`
    - `Veh_Type_ID`: int
    - `Veh_Type_Name`: str
    - `IsAppQuotation`: Optional[int]
    - `Comprehensive`: Optional[str]
    - `TP`: Optional[str]

- **`GET /api/v1/masters/vehicle-types/{id}`**
  - **Path Params**: `id` (int)
  - **Response (200)**: `VehicleTypeResponse`
  - **Response (404)**: Entity not found

#### 2. Vehicle Sub Types
- **`GET /api/v1/masters/vehicle-sub-types`**
  - **Query Params**: `veh_type_id` (Optional[int]), `skip` (int, default 0), `limit` (int, default 100)
  - **Response (200)**: `List[VehicleSubTypeResponse]`
    - `Veh_Sub_Type_ID`: int
    - `Veh_Sub_Type_Name`: str
    - `Veh_Type_ID`: Optional[int]

- **`GET /api/v1/masters/vehicle-sub-types/{id}`**
  - **Path Params**: `id` (int)
  - **Response (200)**: `VehicleSubTypeResponse`

#### 3. Vehicle Makes
- **`GET /api/v1/masters/makes`**
  - **Query Params**: `category` (Optional[str]: `Car`, `TwoWheeler`, `Commercial`, `Passenger`), `search` (Optional[str]), `skip` (int, default 0), `limit` (int, default 100)
  - **Response (200)**: `List[VehicleMakeResponse]`
    - `Make_ID`: int
    - `Make_Name`: str
    - `PvtCar`: Optional[str]
    - `TwoWheeler`: Optional[str]
    - `CommercialVehicle`: Optional[str]
    - `PassengerVehicle`: Optional[str]

- **`GET /api/v1/masters/makes/{id}`**
  - **Path Params**: `id` (int)
  - **Response (200)**: `VehicleMakeResponse`

#### 4. Vehicle Models
- **`GET /api/v1/masters/models`**
  - **Query Params**: `make_id` (Optional[int]), `search` (Optional[str]), `skip` (int, default 0), `limit` (int, default 100)
  - **Response (200)**: `List[VehicleModelResponse]`
    - `Model_ID`: int
    - `Make_ID`: Optional[int]
    - `Model_Name`: str
    - `SegmentId`: Optional[int]

- **`GET /api/v1/masters/models/{id}`**
  - **Path Params**: `id` (int)
  - **Response (200)**: `VehicleModelResponse`

#### 5. Vehicle Variants & Regional Pricing
- **`GET /api/v1/masters/variants`**
  - **Query Params**: `model_id` (Optional[int]), `make_id` (Optional[int]), `search` (Optional[str]), `skip` (int, default 0), `limit` (int, default 100)
  - **Response (200)**: `List[VehicleVariantSummaryResponse]`
    - `Variant_ID`: int
    - `Variance`: str
    - `Model_ID`: Optional[int]
    - `Make_Id`: Optional[int]
    - `CC`: Optional[str]
    - `Seating_Capacity`: Optional[str]
    - `ExMumbai_Model_Price`: Optional[str]

- **`GET /api/v1/masters/variants/{id}`**
  - **Path Params**: `id` (int)
  - **Response (200)**: `VehicleVariantDetailResponse` (Full 91 columns including all 19 cities' Model, Body, and Chassis prices)

- **`GET /api/v1/masters/variants/{id}/price`**
  - **Path Params**: `id` (int)
  - **Query Params**: `city` (Optional[str], default `Mumbai`)
  - **Response (200)**: `VariantRegionalPriceResponse`
    - `variant_id`: int
    - `variant_name`: str
    - `city`: str
    - `effective_ex_showroom_price`: Decimal
    - `model_price`: Decimal
    - `body_price`: Decimal
    - `chassis_price`: Decimal

#### 6. RTO Master
- **`GET /api/v1/masters/rtos`**
  - **Query Params**: `search` (Optional[str]), `district` (Optional[str]), `skip` (int, default 0), `limit` (int, default 100)
  - **Response (200)**: `List[RTOResponse]`
    - `RTOId`: int
    - `RTOLocation`: str
    - `District`: Optional[str]
    - `REG_code`: Optional[str]
    - `ClusterId`: Optional[int]
    - `zone`: Optional[str]

- **`GET /api/v1/masters/rtos/{id}`**
  - **Path Params**: `id` (int)
  - **Response (200)**: `RTOResponse`

#### 7. Insurance Companies
- **`GET /api/v1/masters/insurance-companies`**
  - **Query Params**: `search` (Optional[str]), `skip` (int, default 0), `limit` (int, default 100)
  - **Response (200)**: `List[InsuranceCompanyResponse]`
    - `InsuranceCompanyId`: int
    - `InsuranceCompany`: str
    - `ShortName`: Optional[str]
    - `PolicyNo`: Optional[str]
    - `len`: Optional[int]
    - `CompImgPath`: Optional[str]
    - `LedgerMId`: Optional[int]
    - `ZeroDeep`: Optional[str]
    - `NCB`: Optional[str]

- **`GET /api/v1/masters/insurance-companies/{id}`**
  - **Path Params**: `id` (int)
  - **Response (200)**: `InsuranceCompanyResponse`

---

### 3. Block 2: Underwriting Lookups (`/api/v1/masters`)

- **`GET /api/v1/masters/addons`**
  - **Query Params**: `insurance_company_id` (Optional[int]), `vehicle_type_id` (Optional[int])
  - **Response (200)**: `List[AddonExtraAmtResponse]`
    - `AddonExtraAmtId`: int
    - `InsuranceCompanyId`: Optional[int]
    - `VehiceTypeId`: Optional[int]
    - `NillDep`: Optional[float]
    - `SecurePlus`: Optional[float]

- **`GET /api/v1/masters/pa-owner-driver`**
  - **Query Params**: `insurance_company_id` (Optional[int])
  - **Response (200)**: `List[PAToOwnerDriverResponse]`
    - `PAToOwnerDriverId`: int
    - `InsuranceCompanyId`: Optional[int]
    - `Rate`: Optional[float]
    - `TowingCharges`: Optional[float]

- **`GET /api/v1/masters/towing-rates`**
  - **Query Params**: `insurance_company_id` (Optional[int])
  - **Response (200)**: `List[TowingRateResponse]`
    - `id`: int
    - `InsuranceCompanyId`: Optional[int]
    - `Rate`: Optional[float]
    - `GST18`: Optional[float]
    - `Total`: Optional[float]

- **`GET /api/v1/masters/ncb-slabs`**
  - **Response (200)**: `List[NCBSlabResponse]`
    - `slab_code`: str
    - `slab_percent`: int
    - `description`: str

---

### 4. Block 3: Organizational Masters (`/api/v1/masters`)

- **`GET /api/v1/masters/branches`**
  - **Query Params**: `search` (Optional[str]), `skip` (int, default 0), `limit` (int, default 100)
  - **Response (200)**: `List[BranchResponse]`
    - `BranchId`: int
    - `BranchCode`: str
    - `BranchName`: str
    - `Address`: Optional[str]
    - `ContactNo`: Optional[str]
- **`GET /api/v1/masters/branches/{id}`** -> `BranchResponse`

- **`GET /api/v1/masters/states`**
  - **Query Params**: `search` (Optional[str]), `skip` (int, default 0), `limit` (int, default 100)
  - **Response (200)**: `List[StateResponse]`
    - `StateID`: int
    - `StateName`: str
- **`GET /api/v1/masters/states/{id}`** -> `StateResponse`

- **`GET /api/v1/masters/districts`**
  - **Query Params**: `state_id` (Optional[int]), `search` (Optional[str])
  - **Response (200)**: `List[DistrictResponse]`
    - `DistrictID`: int
    - `DistrictName`: str
    - `StateID`: Optional[int]
- **`GET /api/v1/masters/districts/{id}`** -> `DistrictResponse`

- **`GET /api/v1/masters/banks`**
  - **Query Params**: `search` (Optional[str]), `skip` (int, default 0), `limit` (int, default 100)
  - **Response (200)**: `List[BankResponse]`
    - `BankId`: int
    - `BankName`: str
- **`GET /api/v1/masters/banks/{id}`** -> `BankResponse`

---

### 5. Block 4: Search & Autocomplete Endpoints (`/api/v1/search`)

- **`GET /api/v1/search/autocomplete`**
  - **Query Params**: `category` (str: `agent`, `branch`, `make`, `model`, `bank`, `rto`, `insurer`, `franchise`, `employee`, `surveyor`, `garage`, `ledger`, `claim`, `endorsement`, `state`, `district`, `city`, `pincode`, `cheque`, `voucher`), `q` (str), `parent_id` (Optional[int]), `limit` (int, default 20)
  - **Response (200)**: `AutocompleteResult` (`total`: int, `items`: `List[AutocompleteItem]` [id, text, extra])

- **`GET /api/v1/search/customers`**
  - **Query Params**: `q` (str), `limit` (int, default 20)
  - **Response (200)**: `AutocompleteResult`

- **`GET /api/v1/search/vehicles`**
  - **Query Params**: `q` (str), `limit` (int, default 20)
  - **Response (200)**: `AutocompleteResult`

- **`GET /api/v1/search/policies`**
  - **Query Params**: `q` (str), `search_type` (str: `all`, `cheque`, `clearing`), `limit` (int, default 20)
  - **Response (200)**: `AutocompleteResult`

- **`GET /api/v1/search/inward`**
  - **Query Params**: `q` (str), `limit` (int, default 20)
  - **Response (200)**: `AutocompleteResult`

- **`GET /api/v1/search/quick-check/vehicle-no`**
  - **Query Params**: `registration_no` (str), `financial_year` (Optional[str])
  - **Response (200)**: `DuplicateCheckResponse` (`is_allowed`: bool, `message`: str, `existing_id`: Optional[int])

- **`GET /api/v1/search/quick-check/engine-no`**
  - **Query Params**: `engine_no` (str), `financial_year` (Optional[str])
  - **Response (200)**: `DuplicateCheckResponse`

- **`GET /api/v1/search/quick-check/chassis-no`**
  - **Query Params**: `chassis_no` (str), `financial_year` (Optional[str])
  - **Response (200)**: `DuplicateCheckResponse`

- **`GET /api/v1/search/counters/pending`**
  - **Response (200)**: `PendingCountersResponse`
    - `operator_pending_entries`: int
    - `cheque_pending_count`: int
    - `endorsement_pending_count`: int
    - `claim_pending_count`: int
    - `app_quotation_count`: int
    - `app_policy_count`: int

- **`GET /api/v1/search/dashboard/summary`**
  - **Query Params**: `chart_type` (str: `premium_summary`, `policy_distribution`), `period` (str: `today`, `month`, `year`)
  - **Response (200)**: `DashboardChartResponse`
    - `chart_type`: str
    - `period`: str
    - `labels`: List[str]
    - `series`: List[float]
    - `summary_string`: str

- **`GET /api/v1/search/server-status`**
  - **Response (200)**: `ServerStatusResponse`
    - `status`: str (`ACTIVE`)
    - `server_time`: datetime
    - `version`: str
