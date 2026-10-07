import hmac
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple
import jwt
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status
from app.core.config import settings

# Password hashing context with bcrypt (12 rounds)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

# OAuth2 Bearer scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login",
    auto_error=False
)


def verify_password(plain_password: str, hashed_or_plain_password: str) -> Tuple[bool, bool]:
    """
    Verifies a password against either a modern bcrypt hash or legacy plaintext.
    
    Returns:
        Tuple[bool, bool]:
            - First boolean: is_valid (True if password matches)
            - Second boolean: needs_upgrade (True if password matched plaintext and should be re-hashed to bcrypt)
    
    SAFETY RULE:
        Does NOT automatically modify production users or database records.
        Password migration must never be performed against the legacy production database.
    """
    if not plain_password or not hashed_or_plain_password:
        return False, False

    # Check if the stored string is a bcrypt hash ($2a$, $2b$, $2y$)
    if hashed_or_plain_password.startswith(("$2a$", "$2b$", "$2y$")):
        try:
            is_valid = pwd_context.verify(plain_password, hashed_or_plain_password)
            return is_valid, False
        except Exception:
            return False, False

    # Legacy plaintext check using constant-time comparison to prevent timing attacks
    is_plain_match = hmac.compare_digest(plain_password, hashed_or_plain_password)
    if is_plain_match:
        # Valid match, but needs migration to bcrypt in future write operations
        return True, True

    return False, False


def get_password_hash(password: str) -> str:
    """
    Generates a secure bcrypt hash for a password.
    Never exposes or logs the plain password.
    """
    return pwd_context.hash(password)


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Creates a cryptographically signed JWT access token.
    Never includes password or sensitive credentials in token payload.
    """
    to_encode = data.copy()
    
    # Strip any accidental sensitive fields from token payload
    for sensitive_key in ["password", "UserPassword", "secret", "token"]:
        to_encode.pop(sensitive_key, None)

    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,
        "iat": now,
        "nbf": now,
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decodes and validates a JWT access token.
    Raises HTTPException 401 if invalid or expired.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_token_payload(
    token: Optional[str] = Depends(oauth2_scheme)
) -> Dict[str, Any]:
    """
    Foundational authentication dependency.
    Extracts and validates the JWT Bearer token payload.
    Reusable by future RBAC and ownership verification dependencies.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return decode_access_token(token)
