"""Utilidades de seguridad para las conexiones WebSocket."""

import secrets


def is_valid_api_key(expected: str | None, provided: str | None) -> bool:
    """Compara claves sin revelar cuál parte no coincidió."""
    return bool(expected and provided and secrets.compare_digest(expected, provided))