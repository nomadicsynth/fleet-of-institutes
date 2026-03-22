"""Shared Nexus signing key and public id derivation for main.py and seed.py."""

from __future__ import annotations

import base64
import os

import nacl.signing


def nexus_public_id(signing_key: nacl.signing.SigningKey) -> str:
    """Same string as FastAPI app.state.nexus_id (base64 verify key)."""
    return base64.b64encode(signing_key.verify_key.encode()).decode()


def load_signing_key_from_env() -> nacl.signing.SigningKey | None:
    """Return signing key from NEXUS_SIGNING_KEY, or None if unset."""
    key_b64 = os.environ.get("NEXUS_SIGNING_KEY")
    if not key_b64:
        return None
    return nacl.signing.SigningKey(base64.b64decode(key_b64))


def load_signing_key_for_server() -> nacl.signing.SigningKey:
    """Key for running Nexus: env key if set, else ephemeral (with warning)."""
    sk = load_signing_key_from_env()
    if sk:
        return sk
    sk = nacl.signing.SigningKey.generate()
    print(
        "WARNING: No NEXUS_SIGNING_KEY set — using ephemeral signing key. "
        "Skill package signatures and Nexus identity will change on restart. "
        "Run `python generate_signing_key.py` to create a persistent key."
    )
    return sk
