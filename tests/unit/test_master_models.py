import pytest
from app.models.master import (
    VehicleType,
    VehicleSubType,
    VehicleMake,
    VehicleModel,
    VehicleVariant,
    RTOMaster,
    InsuranceCompany,
)


def test_verified_master_table_names():
    """Verify all 7 Phase 4B master models map to exact verified physical table names."""
    assert VehicleType.__tablename__ == "tbl_vehicle_type"
    assert VehicleSubType.__tablename__ == "tbl_vehicle_sub_type"
    assert VehicleMake.__tablename__ == "tbl_vehicle_make"
    assert VehicleModel.__tablename__ == "tbl_vehicle_model"
    assert VehicleVariant.__tablename__ == "tbl_vehicle_variants"
    assert RTOMaster.__tablename__ == "tbl_rto"
    assert InsuranceCompany.__tablename__ == "tbl_insurancecompany"


def test_verified_master_primary_keys():
    """Verify primary key columns match verified production database physical PKs."""
    assert [c.name for c in VehicleType.__table__.primary_key.columns] == ["Veh_Type_ID"]
    assert [c.name for c in VehicleSubType.__table__.primary_key.columns] == ["Veh_Sub_Type_ID"]
    assert [c.name for c in VehicleMake.__table__.primary_key.columns] == ["Make_ID"]
    assert [c.name for c in VehicleModel.__table__.primary_key.columns] == ["Model_ID"]
    assert [c.name for c in VehicleVariant.__table__.primary_key.columns] == ["Variant_ID"]
    assert [c.name for c in RTOMaster.__table__.primary_key.columns] == ["RTOId"]
    assert [c.name for c in InsuranceCompany.__table__.primary_key.columns] == ["InsuranceCompanyId"]


def test_verified_master_column_counts():
    """
    Verify column counts match verified legacy production database schema exactly:
    - tbl_vehicle_type: 10
    - tbl_vehicle_sub_type: 3
    - tbl_vehicle_make: 12
    - tbl_vehicle_model: 7
    - tbl_vehicle_variants: 91
    - tbl_rto: 10
    - tbl_insurancecompany: 22
    """
    assert len(VehicleType.__table__.columns) == 10
    assert len(VehicleSubType.__table__.columns) == 3
    assert len(VehicleMake.__table__.columns) == 12
    assert len(VehicleModel.__table__.columns) == 7
    assert len(VehicleVariant.__table__.columns) == 91
    assert len(RTOMaster.__table__.columns) == 10
    assert len(InsuranceCompany.__table__.columns) == 22


def test_master_zero_foreign_key_constraints():
    """
    CRITICAL AUDIT CONTRACT:
    Verified legacy production database contains 0 foreign key constraints.
    Master models MUST NOT invent foreign key constraints at the database level.
    """
    models = [
        VehicleType,
        VehicleSubType,
        VehicleMake,
        VehicleModel,
        VehicleVariant,
        RTOMaster,
        InsuranceCompany,
    ]
    for model in models:
        fks = list(model.__table__.foreign_keys)
        assert len(fks) == 0, f"Model {model.__name__} has {len(fks)} unexpected foreign keys: {fks}"


def test_master_mysql_table_args():
    """Verify table arguments specify MySQL UTF-8 charset and DYNAMIC row format."""
    models = [
        VehicleType,
        VehicleSubType,
        VehicleMake,
        VehicleModel,
        VehicleVariant,
        RTOMaster,
        InsuranceCompany,
    ]
    for model in models:
        dialect_options = model.__table__.dialect_options.get("mysql", {})
        assert dialect_options.get("charset") == "utf8", f"{model.__name__} missing mysql_charset"
        assert dialect_options.get("collate") == "utf8_general_ci", f"{model.__name__} missing mysql_collate"
        assert dialect_options.get("row_format") == "DYNAMIC", f"{model.__name__} missing mysql_row_format"


def test_vehicle_variant_91_columns_and_regional_pricing():
    """
    Verify VehicleVariant has all 91 columns including regional ex-showroom pricing matrix,
    legacy metadata, and TAC codes.
    """
    cols = {c.name for c in VehicleVariant.__table__.columns}
    assert len(cols) == 91

    # Check key core attributes
    assert "Variant_ID" in cols
    assert "Veh_Type_ID" in cols
    assert "Veh_Sub_Type_ID" in cols
    assert "Model_ID" in cols
    assert "Make_Tac_Code" in cols
    assert "Model_Tac_Code" in cols
    assert "Variance" in cols
    assert "Tac_Code" in cols
    assert "Wheels" in cols
    assert "Manufacturing_Year" in cols
    assert "CC" in cols
    assert "Seating_Capacity" in cols
    assert "Carrying_Capacity" in cols
    assert "Make_Id" in cols

    # Check regional pricing columns across distinct cities
    cities = [
        "Mumbai", "NewDelhi", "Bangalore", "Kolkatta", "Ahmedabad",
        "Chandigarh", "Shimla", "Faridabad", "Lucknow", "Dehradun",
        "Kohima", "Patna", "Chennai", "Thiruvananthapuram", "Hyderabad",
        "Bhopal", "Raipur", "Jaipur", "Panaji",
    ]
    for city in cities:
        assert f"Ex{city}_Body_Price" in cols, f"Missing Ex{city}_Body_Price"
        assert f"Ex{city}_Model_Price" in cols, f"Missing Ex{city}_Model_Price"
        assert f"Ex{city}_Chasis_Price" in cols, f"Missing Ex{city}_Chasis_Price"


def test_master_specific_data_type_quirks():
    """
    Verify historical data type quirks:
    - tbl_rto.isdeleted is int (nullable)
    - tbl_insurancecompany.isdeleted is varchar (nullable)
    - tbl_vehicle_make.isdeleted is int (non-null, default 0)
    - tbl_vehicle_model.isdeleted is int (non-null, default 0)
    - tbl_insurancecompany.PolicyNo is varchar(500)
    - tbl_insurancecompany.len is int
    """
    rto_isdel = RTOMaster.__table__.columns["isdeleted"]
    assert str(rto_isdel.type).upper() == "INTEGER"

    ins_isdel = InsuranceCompany.__table__.columns["isdeleted"]
    assert "VARCHAR" in str(ins_isdel.type).upper()

    make_isdel = VehicleMake.__table__.columns["isdeleted"]
    assert str(make_isdel.type).upper() == "INTEGER"

    model_isdel = VehicleModel.__table__.columns["isdeleted"]
    assert str(model_isdel.type).upper() == "INTEGER"

    policy_no = InsuranceCompany.__table__.columns["PolicyNo"]
    assert "VARCHAR" in str(policy_no.type).upper()

    len_col = InsuranceCompany.__table__.columns["len"]
    assert str(len_col.type).upper() == "INTEGER"


def test_master_indexes_defined():
    """Verify performance indexes on legacy foreign-key-reference columns exist."""
    sub_type_indexes = {idx.name for idx in VehicleSubType.__table__.indexes}
    assert "tbl_Vehicle_Type" in sub_type_indexes

    model_indexes = {idx.name for idx in VehicleModel.__table__.indexes}
    assert "tbl_Vehicle_Make" in model_indexes

    variant_indexes = {idx.name for idx in VehicleVariant.__table__.indexes}
    assert "tbl_Vehicle_Model" in variant_indexes
    assert "tbl_vehicle_sub_type" in variant_indexes
    assert "tbl_vehicle_type" in variant_indexes
