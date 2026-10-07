import pytest
from app.models.customer import Customer
from app.models.vehicle import VehicleDetails


def test_customer_vehicle_table_names():
    """Verify Customer and VehicleDetails map to exact physical table names."""
    assert Customer.__tablename__ == "tbl_customer"
    assert VehicleDetails.__tablename__ == "tbl_vehicledetails"


def test_customer_vehicle_primary_keys():
    """Verify primary key columns match verified production database physical PKs."""
    assert [c.name for c in Customer.__table__.primary_key.columns] == ["CustomerId"]
    assert [c.name for c in VehicleDetails.__table__.primary_key.columns] == ["CustVehId"]


def test_customer_vehicle_column_counts():
    """
    Verify exact column counts matching legacy schema:
    - tbl_customer: 38 columns
    - tbl_vehicledetails: 32 columns
    """
    assert len(Customer.__table__.columns) == 38
    assert len(VehicleDetails.__table__.columns) == 32


def test_customer_indexes_parity():
    """
    Verify tbl_customer defines the 3 verified production secondary indexes:
    - CustomerCode_UNIQUE: unique=True, prefix length 100 on CustomerCode
    - Fk5_ClientId_idx: non-unique on ClientId
    - Fk18_BranchId_idx: non-unique on BranchId
    """
    indexes = {idx.name: idx for idx in Customer.__table__.indexes}
    assert "CustomerCode_UNIQUE" in indexes
    assert "Fk5_ClientId_idx" in indexes
    assert "Fk18_BranchId_idx" in indexes

    cust_code_idx = indexes["CustomerCode_UNIQUE"]
    assert cust_code_idx.unique is True
    assert [c.name for c in cust_code_idx.columns] == ["CustomerCode"]
    # Check MySQL prefix length option
    mysql_opts = cust_code_idx.dialect_options.get("mysql", {})
    assert mysql_opts.get("length") == 100 or mysql_opts.get("length") == {"CustomerCode": 100}

    client_idx = indexes["Fk5_ClientId_idx"]
    assert client_idx.unique is False
    assert [c.name for c in client_idx.columns] == ["ClientId"]

    branch_idx = indexes["Fk18_BranchId_idx"]
    assert branch_idx.unique is False
    assert [c.name for c in branch_idx.columns] == ["BranchId"]


def test_vehicledetails_indexes_parity():
    """
    Verify tbl_vehicledetails has ZERO secondary indexes in production.
    Only the PRIMARY KEY index exists.
    """
    assert len(VehicleDetails.__table__.indexes) == 0


def test_preserved_spelling_quirks():
    """
    CRITICAL AUDIT CONTRACT:
    Ensure historical legacy spelling quirks and typos are strictly preserved:
    - tbl_customer: MoblieNo1, MoblieNo2 (with 'li')
    - tbl_vehicledetails: CustVehId, ChaiseNo
    Ensure modernized names were NOT introduced.
    """
    cust_cols = {c.name for c in Customer.__table__.columns}
    assert "MoblieNo1" in cust_cols
    assert "MoblieNo2" in cust_cols
    assert "MobileNo1" not in cust_cols
    assert "MobileNo2" not in cust_cols

    veh_cols = {c.name for c in VehicleDetails.__table__.columns}
    assert "CustVehId" in veh_cols
    assert "ChaiseNo" in veh_cols
    assert "ChassisNo" not in veh_cols


def test_vehicle_financial_year_not_null():
    """
    CRITICAL AUDIT CONTRACT:
    FinancialYear is a physical NOT NULL column in tbl_vehicledetails.
    """
    fy_col = VehicleDetails.__table__.columns["FinancialYear"]
    assert fy_col.nullable is False


def test_zero_physical_foreign_keys():
    """
    CRITICAL AUDIT CONTRACT:
    Both tbl_customer and tbl_vehicledetails have 0 physical foreign keys in MySQL.
    Relational integrity is maintained strictly at the application layer.
    """
    assert len(Customer.__table__.foreign_keys) == 0
    assert len(VehicleDetails.__table__.foreign_keys) == 0


def test_customer_vehicle_mysql_table_args():
    """Verify table arguments specify MySQL UTF-8 charset and DYNAMIC row format."""
    for model in [Customer, VehicleDetails]:
        dialect_options = model.__table__.dialect_options.get("mysql", {})
        assert dialect_options.get("charset") == "utf8", f"{model.__name__} missing mysql_charset"
        assert dialect_options.get("collate") == "utf8_general_ci", f"{model.__name__} missing mysql_collate"
        assert dialect_options.get("row_format") == "DYNAMIC", f"{model.__name__} missing mysql_row_format"
