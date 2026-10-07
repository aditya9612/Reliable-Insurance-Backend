import pytest
from app.models.customer import Customer
from app.models.vehicle import VehicleDetails
from app.models.account import Account
from app.models.ledger import LedgerMaster
from app.models.payment import TransactionPayment
from app.models.transaction import Transaction
from app.models.transaction_app import TransactionAppNew
from app.models.commission import FranchiseCommission, AgentCommissionPayment, CutNPayCommPayable


def test_verified_table_names():
    """Verify all 10 Phase 2 models map to exact verified physical table names."""
    assert Customer.__tablename__ == "tbl_customer"
    assert VehicleDetails.__tablename__ == "tbl_vehicledetails"
    assert Account.__tablename__ == "tbl_account"
    assert LedgerMaster.__tablename__ == "tbl_ledgermaster"
    assert TransactionPayment.__tablename__ == "tbl_transactionpayment"
    assert Transaction.__tablename__ == "tbl_transaction"
    assert TransactionAppNew.__tablename__ == "tbl_transactionappnew"
    assert FranchiseCommission.__tablename__ == "tbl_franchisecommission"
    assert AgentCommissionPayment.__tablename__ == "tbl_agentcommissionpayment"
    assert CutNPayCommPayable.__tablename__ == "tbl_cutnpaycommpayable"


def test_verified_primary_keys():
    """Verify primary key columns match verified production database physical PKs."""
    assert [c.name for c in Customer.__table__.primary_key.columns] == ["CustomerId"]
    assert [c.name for c in VehicleDetails.__table__.primary_key.columns] == ["CustVehId"]
    assert [c.name for c in Account.__table__.primary_key.columns] == ["AccountId"]
    assert [c.name for c in LedgerMaster.__table__.primary_key.columns] == ["LedgerMId"]
    assert [c.name for c in TransactionPayment.__table__.primary_key.columns] == ["PaymentId"]
    assert [c.name for c in Transaction.__table__.primary_key.columns] == ["TransanctionId"]
    assert [c.name for c in TransactionAppNew.__table__.primary_key.columns] == ["TransId"]
    assert [c.name for c in FranchiseCommission.__table__.primary_key.columns] == ["FranchiseCommId"]
    assert [c.name for c in AgentCommissionPayment.__table__.primary_key.columns] == ["AgentCommId"]
    assert [c.name for c in CutNPayCommPayable.__table__.primary_key.columns] == ["CutNPayCommPayId"]


def test_verified_column_counts():
    """Verify column counts match verified legacy production database schema exactly."""
    assert len(Customer.__table__.columns) == 38
    assert len(VehicleDetails.__table__.columns) == 32
    assert len(Account.__table__.columns) == 24
    assert len(LedgerMaster.__table__.columns) == 11
    assert len(TransactionPayment.__table__.columns) == 23
    assert len(Transaction.__table__.columns) == 166
    assert len(TransactionAppNew.__table__.columns) == 116
    assert len(FranchiseCommission.__table__.columns) == 29
    assert len(AgentCommissionPayment.__table__.columns) == 20
    assert len(CutNPayCommPayable.__table__.columns) == 11


def test_verified_naming_quirks_preserved():
    """
    CRITICAL AUDIT CONTRACT:
    Ensure historical legacy spelling quirks and typos are preserved in physical columns:
    - tbl_transaction: TransanctionId, ODPermium, TPPermium, NetPermium, TStatus
    - tbl_vehicledetails: CustVehId, RegistrationNo, ChaiseNo
    - tbl_customer: MoblieNo1, MoblieNo2
    - tbl_account: IsNill
    """
    trans_cols = {c.name for c in Transaction.__table__.columns}
    assert "TransanctionId" in trans_cols
    assert "ODPermium" in trans_cols
    assert "TPPermium" in trans_cols
    assert "NetPermium" in trans_cols
    assert "TStatus" in trans_cols

    # Ensure incorrect clean names were NOT silently used
    assert "ODPremium" not in trans_cols
    assert "TPPremium" not in trans_cols
    assert "NetPremium" not in trans_cols

    veh_cols = {c.name for c in VehicleDetails.__table__.columns}
    assert "CustVehId" in veh_cols
    assert "RegistrationNo" in veh_cols
    assert "ChaiseNo" in veh_cols

    cust_cols = {c.name for c in Customer.__table__.columns}
    assert "MoblieNo1" in cust_cols
    assert "MoblieNo2" in cust_cols

    acc_cols = {c.name for c in Account.__table__.columns}
    assert "IsNill" in acc_cols


def test_zero_foreign_key_constraints():
    """
    CRITICAL AUDIT CONTRACT:
    Verified production database contains 0 foreign key constraints.
    Models MUST NOT invent foreign key constraints at the database level.
    """
    models = [
        Customer,
        VehicleDetails,
        Account,
        LedgerMaster,
        TransactionPayment,
        Transaction,
        TransactionAppNew,
        FranchiseCommission,
        AgentCommissionPayment,
        CutNPayCommPayable,
    ]
    for model in models:
        fks = list(model.__table__.foreign_keys)
        assert len(fks) == 0, f"Model {model.__name__} has {len(fks)} unexpected foreign keys: {fks}"


def test_mysql_table_args():
    """Verify table arguments specify MySQL UTF-8 charset and DYNAMIC row format."""
    models = [
        Customer,
        VehicleDetails,
        Account,
        LedgerMaster,
        TransactionPayment,
        Transaction,
        TransactionAppNew,
        FranchiseCommission,
        AgentCommissionPayment,
        CutNPayCommPayable,
    ]
    for model in models:
        dialect_options = model.__table__.dialect_options.get("mysql", {})
        assert dialect_options.get("charset") == "utf8", f"{model.__name__} missing mysql_charset"
        assert dialect_options.get("collate") == "utf8_general_ci", f"{model.__name__} missing mysql_collate"
        assert dialect_options.get("row_format") == "DYNAMIC", f"{model.__name__} missing mysql_row_format"
