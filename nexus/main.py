import asyncio
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from config import FEDERATION_ENABLED, FEDERATION_RETRY_INTERVAL, NEXUS_PEERS
from nexus_identity import load_signing_key_for_server, nexus_public_id
from database import get_connection, init_db, insert_peer, get_peer_by_url
from middleware import (
    BodySizeLimitMiddleware,
    RateLimitMiddleware,
    RequestLoggingMiddleware,
)
from routes import institutes, papers, feed, ws, skill

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = _connect_with_retry()
    init_db(conn)
    app.state.db = conn

    signing_key = load_signing_key_for_server()
    app.state.signing_key = signing_key
    app.state.nexus_id = nexus_public_id(signing_key)

    log.info("Nexus ID (public key): %s", app.state.nexus_id)

    if FEDERATION_ENABLED:
        await _bootstrap_peers(conn)
        await _initial_sync(conn, app.state.nexus_id, signing_key)
        app.state._federation_task = asyncio.create_task(
            _federation_retry_loop(conn, signing_key)
        )

    yield

    if FEDERATION_ENABLED and hasattr(app.state, "_federation_task"):
        app.state._federation_task.cancel()
        try:
            await app.state._federation_task
        except asyncio.CancelledError:
            pass

    conn.close()


def _connect_with_retry(max_attempts: int = 30, delay: float = 2.0):
    """Retry connecting to MariaDB — gives the database container time to start."""
    for attempt in range(1, max_attempts + 1):
        try:
            return get_connection()
        except Exception as exc:
            if attempt == max_attempts:
                raise
            print(f"DB connection attempt {attempt}/{max_attempts} failed: {exc}. Retrying in {delay}s...")
            time.sleep(delay)


async def _bootstrap_peers(conn):
    """Seed the peers table from the NEXUS_PEERS env var."""
    if not NEXUS_PEERS:
        return
    import httpx
    for url in NEXUS_PEERS.split(","):
        url = url.strip().rstrip("/")
        if not url:
            continue
        existing = get_peer_by_url(conn, url)
        if existing:
            continue

        public_key = ""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{url}/federation/identity")
            if resp.status_code == 200:
                public_key = resp.json().get("public_key", "")
        except Exception as exc:
            log.warning("Could not reach peer %s for identity handshake: %s", url, exc)

        insert_peer(conn, url, public_key)
        log.info("Registered bootstrap peer: %s (key: %s)", url, public_key[:16] + "..." if public_key else "unknown")


async def _initial_sync(conn, nexus_id: str, signing_key):
    """Pull metadata from all peers on startup."""
    from database import get_peers
    from federation import sync_metadata_from_peer

    peers = get_peers(conn)
    for peer in peers:
        try:
            count = await sync_metadata_from_peer(conn, peer["url"], nexus_id, signing_key)
            if count:
                log.info("Synced %d items from peer %s", count, peer["url"])
        except Exception as exc:
            log.warning("Initial sync from %s failed: %s", peer["url"], exc)


async def _federation_retry_loop(conn, signing_key):
    """Background task that retries failed federation deliveries."""
    from federation import retry_failed_deliveries
    while True:
        await asyncio.sleep(FEDERATION_RETRY_INTERVAL)
        try:
            count = await retry_failed_deliveries(conn, signing_key)
            if count:
                log.info("Retried %d failed federation deliveries", count)
        except Exception as exc:
            log.warning("Federation retry error: %s", exc)


app = FastAPI(
    title="Fleet of Institutes Nexus",
    description="An open research commons where AI-augmented research institutes publish, cite, review, and build on each other's work.",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(BodySizeLimitMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "X-Skill-Signature",
        "X-Skill-Public-Key",
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "Retry-After",
    ],
)

app.include_router(institutes.router)
app.include_router(papers.router)
app.include_router(feed.router)
app.include_router(ws.router)
app.include_router(skill.router)

if FEDERATION_ENABLED:
    from routes import federation
    app.include_router(federation.router)


@app.get("/", tags=["meta"])
async def root(request: Request):
    return {
        "name": "Fleet of Institutes Nexus",
        "version": "0.2.0",
        "docs": "/docs",
        "skill": "/skill",
        "federation": FEDERATION_ENABLED,
        "nexus_id": request.app.state.nexus_id,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
