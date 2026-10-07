import pytest
from datetime import timedelta
from fastapi import HTTPException
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_access_token,
)


def test_bcrypt_hashing_and_verification():
    """Verify modern bcrypt password hashing and verification."""
    password = "SuperSecurePassword123!"
    hashed = get_password_hash(password)
    
    assert hashed != password
    assert hashed.startswith(("$2a$", "$2b$", "$2y$"))

    # Correct password
    is_valid, needs_upgrade = verify_password(password, hashed)
    assert is_valid is True
    assert needs_upgrade is False

    # Incorrect password
    is_valid, needs_upgrade = verify_password("WrongPassword!", hashed)
    assert is_valid is False
    assert needs_upgrade is False


def test_legacy_plaintext_password_verification():
    """
    Verify legacy plaintext password verification logic.
    Matches plaintext and signals needs_upgrade=True WITHOUT touching production DB.
    """
    legacy_plain = "UserLegacyPass2026"

    # Match against plaintext stored password
    is_valid, needs_upgrade = verify_password(legacy_plain, legacy_plain)
    assert is_valid is True
    assert needs_upgrade is True

    # Mismatch against plaintext stored password
    is_valid, needs_upgrade = verify_password("IncorrectPass", legacy_plain)
    assert is_valid is False
    assert needs_upgrade is False


def test_empty_password_handling():
    """Verify empty or None passwords return False safely."""
    assert verify_password("", "somehash") == (False, False)
    assert verify_password("somepass", "") == (False, False)


def test_jwt_creation_and_decoding():
    """Verify JWT token issuance, payload preservation, and validation."""
    data = {
        "sub": "42",
        "user_id": 42,
        "username": "agent_rahul",
        "role_id": 3,
        "branch_id": 105,
    }
    token = create_access_token(data)
    assert isinstance(token, str)

    payload = decode_access_token(token)
    assert payload["sub"] == "42"
    assert payload["user_id"] == 42
    assert payload["username"] == "agent_rahul"
    assert payload["role_id"] == 3
    assert payload["branch_id"] == 105
    assert "exp" in payload
    assert "iat" in payload


def test_jwt_strips_sensitive_password_keys():
    """Ensure sensitive password fields are never embedded into JWT tokens."""
    data = {
        "sub": "100",
        "username": "clerk1",
        "password": "mypassword",
        "UserPassword": "legacyuserpass",
    }
    token = create_access_token(data)
    payload = decode_access_token(token)
    
    assert "password" not in payload
    assert "UserPassword" not in payload


def test_expired_jwt_raises_401():
    """Verify that expired JWT tokens raise HTTP 401 Unauthorized."""
    data = {"sub": "99"}
    # Create token expired 1 minute ago
    token = create_access_token(data, expires_delta=timedelta(minutes=-1))
    
    with pytest.raises(HTTPException) as exc_info:
        decode_access_token(token)
    assert exc_info.value.status_code == 401
    assert "expired" in exc_info.value.detail.lower()
