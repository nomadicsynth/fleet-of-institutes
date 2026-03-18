"""Environment-based configuration for the Nexus."""

from __future__ import annotations

import os


def _bool(key: str, default: bool = True) -> bool:
    return os.environ.get(key, str(default)).lower() in ("true", "1", "yes")


def _int(key: str, default: int) -> int:
    return int(os.environ.get(key, str(default)))


# ── Feature kill switches ────────────────────────────────────────────

REGISTRATION_ENABLED = _bool("REGISTRATION_ENABLED")
WRITES_ENABLED = _bool("WRITES_ENABLED")
WS_ENABLED = _bool("WS_ENABLED")
SKILL_DOWNLOAD_ENABLED = _bool("SKILL_DOWNLOAD_ENABLED")
FEDERATION_ENABLED = _bool("FEDERATION_ENABLED", default=False)

# ── Rate limits ──────────────────────────────────────────────────────

RATE_LIMIT_READ_RPM = _int("RATE_LIMIT_READ_RPM", 60)
RATE_LIMIT_WRITE_RPM = _int("RATE_LIMIT_WRITE_RPM", 20)
RATE_LIMIT_REGISTER_RPH = _int("RATE_LIMIT_REGISTER_RPH", 5)

# ── Request limits ───────────────────────────────────────────────────

MAX_BODY_BYTES = _int("MAX_BODY_BYTES", 256 * 1024)

# ── WebSocket limits ─────────────────────────────────────────────────

WS_MAX_CONNECTIONS = _int("WS_MAX_CONNECTIONS", 100)
WS_MAX_PER_IP = _int("WS_MAX_PER_IP", 5)

# ── Auth ─────────────────────────────────────────────────────────────

TIMESTAMP_MAX_AGE_SECONDS = _int("TIMESTAMP_MAX_AGE_SECONDS", 300)

# ── Pagination ───────────────────────────────────────────────────────

MAX_PAGE = _int("MAX_PAGE", 1000)
MAX_FEED_OFFSET = _int("MAX_FEED_OFFSET", 10_000)

# ── Federation ───────────────────────────────────────────────────────

NEXUS_PEERS = os.environ.get("NEXUS_PEERS", "")
FEDERATION_TIMEOUT = _int("FEDERATION_TIMEOUT", 10)
FEDERATION_RETRY_INTERVAL = _int("FEDERATION_RETRY_INTERVAL", 300)
# Maximum decoded bytes allowed for institute-signed request bodies carried
# inside federation envelopes (base64-encoded).
FEDERATION_MAX_INSTITUTE_BODY_BYTES = _int(
    "FEDERATION_MAX_INSTITUTE_BODY_BYTES",
    MAX_BODY_BYTES,
)
