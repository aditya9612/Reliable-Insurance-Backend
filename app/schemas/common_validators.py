"""
Canonical Input Validators for Reliable Insurance Backend Schemas.
Centralizes validation for Indian mobile numbers, PAN, Aadhaar, PIN, IFSC, and Email syntax.
"""
import re
from typing import Optional
from email_validator import validate_email as _validate_email, EmailNotValidError

_PAN_REGEX = re.compile(r"^[A-Za-z]{5}[0-9]{4}[A-Za-z]{1}$")
_AADHAAR_REGEX = re.compile(r"^[0-9]{12}$")
_PIN_REGEX = re.compile(r"^[1-9][0-9]{5}$")
_IFSC_REGEX = re.compile(r"^[A-Za-z]{4}0[A-Za-z0-9]{6}$")
_MOBILE_CLEAN_REGEX = re.compile(r"^[6-9]\d{9}$")
_EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)+$")


def validate_indian_mobile(v: Optional[str]) -> Optional[str]:
    """
    Validates and normalizes Indian 10-digit mobile numbers.
    Accepts numbers starting with 6, 7, 8, 9 with optional +91, 91, or 0 prefixes.
    Whitespace, hyphens, and parentheses are stripped.
    """
    if v is None:
        return None
    s = "".join(ch for ch in str(v) if ch not in (" ", "-", "(", ")", "."))
    if not s:
        return None
    if s.startswith("+91"):
        s = s[3:]
    elif s.startswith("91") and len(s) == 12:
        s = s[2:]
    elif s.startswith("0") and len(s) == 11:
        s = s[1:]
    if not _MOBILE_CLEAN_REGEX.fullmatch(s):
        raise ValueError("Mobile number must be a valid 10-digit Indian phone number starting with 6, 7, 8, or 9")
    return s


def validate_pan(v: Optional[str]) -> Optional[str]:
    """
    Validates Indian Income Tax PAN format (5 letters, 4 digits, 1 letter).
    Preserves casing for legacy compatibility while strictly enforcing structure.
    """
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    if not _PAN_REGEX.fullmatch(s):
        raise ValueError("Invalid PAN format. Must be 10 characters (5 letters, 4 digits, 1 letter, e.g. ABCDE1234F)")
    return s


def validate_aadhaar(v: Optional[str]) -> Optional[str]:
    """
    Validates 12-digit Indian Aadhaar number.
    Whitespace and hyphens are stripped before validation.
    """
    if v is None:
        return None
    s = "".join(ch for ch in str(v) if ch not in (" ", "-"))
    if not s:
        return None
    if not _AADHAAR_REGEX.fullmatch(s):
        raise ValueError("Invalid Aadhaar format. Must be exactly 12 numeric digits")
    return s


def validate_pin_code(v: Optional[str]) -> Optional[str]:
    """
    Validates Indian Postal Index Number (PIN Code: 6 digits, first digit 1-9).
    """
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    if not _PIN_REGEX.fullmatch(s):
        raise ValueError("Invalid PIN code. Must be 6 numeric digits starting with 1-9 (e.g. 411001)")
    return s


def validate_ifsc(v: Optional[str]) -> Optional[str]:
    """
    Validates Indian Financial System Code (IFSC: 4 letters, '0', 6 alphanumeric chars).
    Normalizes to uppercase.
    """
    if v is None:
        return None
    s = str(v).strip().upper()
    if not s:
        return None
    if not _IFSC_REGEX.fullmatch(s):
        raise ValueError("Invalid IFSC code format (e.g. SBIN0001234)")
    return s


def validate_email_syntax(v: Optional[str]) -> Optional[str]:
    """
    Validates email address syntax (e.g. user@domain.com or user@company.local).
    Returns cleaned email string.
    """
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    if not _EMAIL_REGEX.fullmatch(s):
        raise ValueError("Invalid email address format (e.g. user@example.com)")
    return s
