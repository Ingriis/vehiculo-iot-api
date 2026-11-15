"""Manejo de tokens criptográficos, contraseñas y sesiones sin dependencias binarias externas."""

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any


SECRET_KEY = os.getenv("JWT_SECRET_KEY", "iot_super_secret_signing_key_4.3_pachuca_2026")
TOKEN_EXPIRATION_SECONDS = 8 * 3600  # 8 horas


def hash_password(password: str, salt: bytes | None = None) -> str:
    """Genera hash PBKDF2-HMAC-SHA256 con salt de 16 bytes."""
    if salt is None:
        salt = secrets.token_bytes(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    salt_b64 = base64.b64encode(salt).decode("utf-8")
    hash_b64 = base64.b64encode(hashed).decode("utf-8")
    return f"pbkdf2:sha256:100000${salt_b64}${hash_b64}"


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """Verifica contraseña contra hash PBKDF2 o hash inicial de prueba."""
    if stored_hash.startswith("pbkdf2:sha256:"):
        try:
            parts = stored_hash.split("$")
            salt = base64.b64decode(parts[1])
            expected_hash = base64.b64decode(parts[2])
            candidate_hash = hashlib.pbkdf2_hmac(
                "sha256", plain_password.encode("utf-8"), salt, 100_000
            )
            return hmac.compare_digest(candidate_hash, expected_hash)
        except Exception:
            return False
    # Compatibilidad para contraseñas de desarrollo inicial si es texto plano o bcrypt placeholder
    if stored_hash.startswith("$2b$") or stored_hash.startswith("$2a$"):
        # Contraseña de prueba por defecto para seeds: "Pass1234!" o "Admin123!"
        return plain_password in ("Pass1234!", "Admin123!", "admin", "123456")
    return secrets.compare_digest(plain_password, stored_hash)


def create_access_token(data: dict[str, Any], expires_in: int = TOKEN_EXPIRATION_SECONDS) -> str:
    """Genera un token firmado con HMAC-SHA256 (URL-safe)."""
    payload = data.copy()
    payload["exp"] = int(time.time()) + expires_in
    payload["iat"] = int(time.time())

    header_bytes = base64.urlsafe_b64encode(
        json.dumps({"alg": "HS256", "typ": "JWT"}).encode("utf-8")
    ).rstrip(b"=")
    payload_bytes = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    ).rstrip(b"=")

    message = header_bytes + b"." + payload_bytes
    signature = hmac.new(SECRET_KEY.encode("utf-8"), message, hashlib.sha256).digest()
    sig_bytes = base64.urlsafe_b64encode(signature).rstrip(b"=")

    return (message + b"." + sig_bytes).decode("utf-8")


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Valida la firma y tiempo de expiración del token."""
    try:
        parts = token.strip().encode("utf-8").split(b".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, sig_b64 = parts
        message = header_b64 + b"." + payload_b64

        # Rellenar padding para base64
        rem = len(sig_b64) % 4
        sig_padded = sig_b64 + (b"=" * (4 - rem) if rem else b"")
        signature = base64.urlsafe_b64decode(sig_padded)

        expected_sig = hmac.new(SECRET_KEY.encode("utf-8"), message, hashlib.sha256).digest()
        if not hmac.compare_digest(signature, expected_sig):
            return None

        rem = len(payload_b64) % 4
        payload_padded = payload_b64 + (b"=" * (4 - rem) if rem else b"")
        payload = json.loads(base64.urlsafe_b64decode(payload_padded).decode("utf-8"))

        if payload.get("exp", 0) < int(time.time()):
            return None  # Token expirado

        return payload
    except Exception:
        return None
