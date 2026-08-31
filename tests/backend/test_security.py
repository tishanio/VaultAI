"""Tests for security utilities — JWT, password hashing, encryption."""
import uuid

from vault.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
    encrypt_data,
    decrypt_data,
    encrypt_short,
    decrypt_short,
)


def test_hash_password():
    hashed = hash_password("mypassword")
    assert hashed != "mypassword"
    assert verify_password("mypassword", hashed)


def test_hash_password_wrong():
    hashed = hash_password("mypassword")
    assert not verify_password("wrongpassword", hashed)


def test_create_access_token():
    user_id = str(uuid.uuid4())
    token = create_access_token(user_id, {"username": "testuser"})
    assert isinstance(token, str)
    assert len(token) > 50


def test_decode_access_token():
    user_id = str(uuid.uuid4())
    token = create_access_token(user_id, {"username": "testuser"})
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == user_id
    assert payload["username"] == "testuser"
    assert payload["type"] == "access"


def test_create_refresh_token():
    user_id = str(uuid.uuid4())
    token = create_refresh_token(user_id)
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == user_id
    assert payload["type"] == "refresh"


def test_decode_invalid_token():
    payload = decode_token("invalid.token.here")
    assert payload is None


def test_encrypt_decrypt_data():
    plaintext = "super secret credential data"
    encrypted = encrypt_data(plaintext)
    assert encrypted != plaintext
    decrypted = decrypt_data(encrypted)
    assert decrypted == plaintext


def test_encrypt_decrypt_short():
    value = "short_value"
    encrypted = encrypt_short(value)
    assert encrypted != value
    decrypted = decrypt_short(encrypted)
    assert decrypted == value
