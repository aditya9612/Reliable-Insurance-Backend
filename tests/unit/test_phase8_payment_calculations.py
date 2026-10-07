"""
Phase 8 Unit Tests — Payment Instrument Validation, Cheque Bounce & Penalty Math,
Payment Reversal Math, Insurer Reconciliation Variance Math, and Decimal Rounding Invariants.
"""
from decimal import Decimal
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.schemas.payment import (
    ChequeBounceRequest,
    ReconciliationMatchRequest,
    WalletDebitRequest,
    WalletLockRequest,
    WalletReleaseRequest,
    WalletTopupRequest,
)
from app.schemas.policy import PaymentInstrumentCreateRequest
from app.services.payment_engine import (
    calculate_cheque_bounce_effect,
    calculate_payment_reversal_effect,
    evaluate_payment_instrument_state,
    evaluate_reconciliation_match,
    round_2dp,
)


# ===========================================================================
# 1. Payment Instrument Type & Cheque/DD Mandatory Field Validation
# ===========================================================================


@pytest.mark.parametrize(
    "payment_type,expected_status,expected_cashier_approval",
    [
        ("CASH", "RECEIVED", 1),
        ("ONLINE", "RECEIVED", 1),
        ("NEFT", "RECEIVED", 1),
        ("RTGS", "RECEIVED", 1),
        ("UPI", "RECEIVED", 1),
        ("CREDIT_CARD", "RECEIVED", 1),
        ("DEBIT_CARD", "RECEIVED", 1),
        ("CUTNPAY", "RECEIVED", 1),
        ("EWALLET", "RECEIVED", 1),
        ("DIRECT_TO_INSURER", "RECEIVED", 1),
        ("CHEQUE", "PENDING_CLEARANCE", 0),
        ("DD", "PENDING_CLEARANCE", 0),
    ],
)
def test_evaluate_payment_instrument_state_all_modes(
    payment_type: str,
    expected_status: str,
    expected_cashier_approval: int,
):
    status_str, cashier_app = evaluate_payment_instrument_state(payment_type)
    assert status_str == expected_status
    assert cashier_app == expected_cashier_approval


@pytest.mark.parametrize("cheque_mode", ["CHEQUE", "DD"])
def test_cheque_and_dd_require_docno_and_bankname(cheque_mode: str):
    # Missing both docno and bankname -> ValidationError
    with pytest.raises(ValidationError):
        PaymentInstrumentCreateRequest(
            payment_type=cheque_mode,
            paid_amount=Decimal("5000.00"),
        )

    # Missing bankname -> ValidationError
    with pytest.raises(ValidationError):
        PaymentInstrumentCreateRequest(
            payment_type=cheque_mode,
            paid_amount=Decimal("5000.00"),
            docno="CHQ100200",
        )

    # Missing docno -> ValidationError
    with pytest.raises(ValidationError):
        PaymentInstrumentCreateRequest(
            payment_type=cheque_mode,
            paid_amount=Decimal("5000.00"),
            bankname="HDFC BANK",
        )

    # Valid when both docno and bankname are present
    req = PaymentInstrumentCreateRequest(
        payment_type=cheque_mode,
        paid_amount=Decimal("5000.00"),
        docno="CHQ100200",
        bankname="HDFC BANK",
    )
    assert req.payment_type == cheque_mode
    assert req.paid_amount == Decimal("5000.00")


def test_invalid_payment_type_rejected():
    with pytest.raises(ValidationError):
        PaymentInstrumentCreateRequest(
            payment_type="CRYPTO_COIN",
            paid_amount=Decimal("1000.00"),
        )


# ===========================================================================
# 2. Cheque Bounce & Dishonor Penalty Math
# ===========================================================================


def test_calculate_cheque_bounce_effect_without_penalty():
    new_paid, new_out, contra = calculate_cheque_bounce_effect(
        current_paid=Decimal("11800.00"),
        current_outstanding=Decimal("0.00"),
        cheque_amount=Decimal("11800.00"),
        penalty_amount=Decimal("0.00"),
    )
    assert new_paid == Decimal("0.00")
    assert new_out == Decimal("11800.00")
    assert contra == Decimal("-11800.00")


def test_calculate_cheque_bounce_effect_with_penalty_and_partial_cash():
    # Policy Final = 15000: Cash 5000 + Cheque 10000 (Paid = 15000, Out = 0)
    # Cheque 10000 bounces with 500 penalty -> New Paid = 5000, New Out = 10500, Contra = -10000
    new_paid, new_out, contra = calculate_cheque_bounce_effect(
        current_paid=Decimal("15000.00"),
        current_outstanding=Decimal("0.00"),
        cheque_amount=Decimal("10000.00"),
        penalty_amount=Decimal("500.00"),
    )
    assert new_paid == Decimal("5000.00")
    assert new_out == Decimal("10500.00")
    assert contra == Decimal("-10000.00")


def test_cheque_bounce_negative_penalty_rejected_by_schema():
    with pytest.raises(ValidationError):
        ChequeBounceRequest(
            bounce_reason="Insufficient Funds",
            penalty_amount=Decimal("-100.00"),
        )


# ===========================================================================
# 3. Payment Reversal Math
# ===========================================================================


def test_calculate_payment_reversal_effect():
    new_paid, new_out, contra = calculate_payment_reversal_effect(
        current_paid=Decimal("11800.00"),
        current_outstanding=Decimal("0.00"),
        reversed_amount=Decimal("4800.00"),
    )
    assert new_paid == Decimal("7000.00")
    assert new_out == Decimal("4800.00")
    assert contra == Decimal("-4800.00")


# ===========================================================================
# 4. Insurer Payment & Brokerage Reconciliation Math
# ===========================================================================


def test_evaluate_reconciliation_exact_match():
    eff_grid, eff_comm, variance, match_flag, match_status = evaluate_reconciliation_match(
        net_premium=Decimal("10000.00"),
        booked_gross_comm=Decimal("1500.00"),
        reconciled_grid_percent=Decimal("15.00"),
        reconciled_comm_amount=None,
    )
    assert eff_grid == Decimal("15.00")
    assert eff_comm == Decimal("1500.00")
    assert variance == Decimal("0.00")
    assert match_flag == 1
    assert match_status == "MATCHED"


def test_evaluate_reconciliation_within_one_rupee_tolerance():
    eff_grid, eff_comm, variance, match_flag, match_status = evaluate_reconciliation_match(
        net_premium=Decimal("10000.00"),
        booked_gross_comm=Decimal("1500.00"),
        reconciled_comm_amount=Decimal("1500.75"),
    )
    assert eff_comm == Decimal("1500.75")
    assert variance == Decimal("0.75")
    assert match_flag == 1
    assert match_status == "MATCHED"


def test_evaluate_reconciliation_partial_variance_allowed_vs_rejected():
    eff_grid, eff_comm, variance, match_flag, match_status = evaluate_reconciliation_match(
        net_premium=Decimal("10000.00"),
        booked_gross_comm=Decimal("1500.00"),
        reconciled_grid_percent=Decimal("12.00"),
        allow_partial_match=True,
    )
    assert eff_grid == Decimal("12.00")
    assert eff_comm == Decimal("1200.00")
    assert variance == Decimal("-300.00")
    assert match_flag == 2
    assert match_status == "PARTIAL_VARIANCE"

    # When allow_partial_match=False, variance > 1.00 raises 422 HTTPException
    with pytest.raises(HTTPException) as exc_info:
        evaluate_reconciliation_match(
            net_premium=Decimal("10000.00"),
            booked_gross_comm=Decimal("1500.00"),
            reconciled_grid_percent=Decimal("12.00"),
            allow_partial_match=False,
        )
    assert exc_info.value.status_code == 422


# ===========================================================================
# 5. Wallet Request Schema Validation & Decimal Rounding
# ===========================================================================


def test_wallet_schemas_reject_non_positive_amounts_and_missing_release_target():
    with pytest.raises(ValidationError):
        WalletTopupRequest(owner_type="AGENT", owner_id=101, amount=Decimal("0.00"))

    with pytest.raises(ValidationError):
        WalletLockRequest(owner_type="AGENT", owner_id=101, amount=Decimal("-50.00"))

    with pytest.raises(ValidationError):
        WalletDebitRequest(owner_type="FRANCHISE", owner_id=201, amount=Decimal("0.00"))

    # WalletReleaseRequest requires either lock_account_id or proposal_trans_id
    with pytest.raises(ValidationError):
        WalletReleaseRequest(reason="Missing target IDs")

    valid_rel = WalletReleaseRequest(lock_account_id=42, reason="Proposal expired")
    assert valid_rel.lock_account_id == 42


def test_round_2dp_half_up_deterministic():
    assert round_2dp(Decimal("123.455")) == Decimal("123.46")
    assert round_2dp(Decimal("123.454")) == Decimal("123.45")
    assert round_2dp(Decimal("0.005")) == Decimal("0.01")
