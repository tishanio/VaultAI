from __future__ import annotations

"""Security utilities — JWT, password hashing, AES-256-GCM encryption."""
import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import bcrypt
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from jose import JWTError, jwt

from vault.config import settings


# ---------------------------------------------------------------------------
# RSA Key Management
# ---------------------------------------------------------------------------

def _load_or_generate_rsa_keys():
    """Load RSA keys from disk, or generate and save a new pair."""
    private_path = Path(settings.JWT_PRIVATE_KEY_PATH)
    public_path = Path(settings.JWT_PUBLIC_KEY_PATH)

    if private_path.exists() and public_path.exists():
        private_key = private_path.read_bytes()
        public_key = public_path.read_bytes()
        return private_key, public_key

    private_key_obj = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_key = private_key_obj.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_key = private_key_obj.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    private_path.parent.mkdir(parents=True, exist_ok=True)
    private_path.write_bytes(private_key)
    private_path.chmod(0o600)
    public_path.write_bytes(public_key)

    return private_key, public_key


PRIVATE_KEY, PUBLIC_KEY = _load_or_generate_rsa_keys()


# ---------------------------------------------------------------------------
# JWT Tokens
# ---------------------------------------------------------------------------

def create_access_token(subject: str, extra_claims: dict[str, Any] | None = None) -> str:
    """Create a short-lived JWT access token."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
        "type": "access",
        "jti": secrets.token_urlsafe(16),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, PRIVATE_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: str) -> str:
    """Create a long-lived JWT refresh token."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
        "type": "refresh",
        "jti": secrets.token_urlsafe(16),
    }
    return jwt.encode(payload, PRIVATE_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any] | None:
    """Decode and validate a JWT token. Returns None if invalid."""
    try:
        payload = jwt.decode(token, PUBLIC_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


# ---------------------------------------------------------------------------
# Password Hashing
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a bcrypt hash."""
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


# ---------------------------------------------------------------------------
# AES-256-GCM Encryption (for credential vaulting)
# ---------------------------------------------------------------------------

def _get_encryption_key() -> bytes:
    """Derive or load the AES-256 encryption key."""
    if settings.ENCRYPTION_KEY:
        return base64.b64decode(settings.ENCRYPTION_KEY)[:32]
    # Fallback: derive from secret key (only for demo; use AWS Secrets Manager in prod)
    return hashlib.sha256(settings.SECRET_KEY.encode()).digest()


def encrypt_data(plaintext: str) -> str:
    """Encrypt plaintext using AES-256-GCM. Returns base64-encoded (nonce + ciphertext)."""
    key = _get_encryption_key()
    aesgcm = AESGCM(key)
    nonce = secrets.token_bytes(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    combined = nonce + ciphertext
    return base64.b64encode(combined).decode("utf-8")


def decrypt_data(encrypted: str) -> str:
    """Decrypt AES-256-GCM encrypted data."""
    key = _get_encryption_key()
    combined = base64.b64decode(encrypted)
    nonce = combined[:12]
    ciphertext = combined[12:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")


# ---------------------------------------------------------------------------
# Fernet (simpler symmetric encryption for short values)
# ---------------------------------------------------------------------------

def _fernet() -> Fernet:
    """Return a Fernet instance keyed from the application secret."""
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.SECRET_KEY.encode()).digest())
    return Fernet(key)


def encrypt_short(value: str) -> str:
    """Encrypt a short string value with Fernet."""
    return _fernet().encrypt(value.encode()).decode()


def decrypt_short(encrypted: str) -> str:
    """Decrypt a Fernet-encrypted short string."""
    return _fernet().decrypt(encrypted.encode()).decode()
