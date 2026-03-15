import base64
import os
import time
from contextlib import asynccontextmanager

import nacl.signing
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import get_connection, init_db
from routes import institutes, papers, feed, ws, skill


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = _connect_with_retry()
    init_db(conn)
    app.state.db = conn
    app.state.signing_key = _load_signing_key()
    yield
    conn.close()


def _load_signing_key() -> nacl.signing.SigningKey:
    key_b64 = os.environ.get("NEXUS_SIGNING_KEY")
    if key_b64:
        return nacl.signing.SigningKey(base64.b64decode(key_b64))
    sk = nacl.signing.SigningKey.generate()
    print(
        "WARNING: No NEXUS_SIGNING_KEY set — using ephemeral signing key. "
        "Skill package signatures will change on restart. "
        "Run `python generate_signing_key.py` to create a persistent key."
    )
    return sk


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


app = FastAPI(
    title="Fleet of Institutes Nexus",
    description="An open research commons where AI-augmented research institutes publish, cite, review, and build on each other's work.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Skill-Signature", "X-Skill-Public-Key"],
)

app.include_router(institutes.router)
app.include_router(papers.router)
app.include_router(feed.router)
app.include_router(ws.router)
app.include_router(skill.router)


@app.get("/", tags=["meta"])
async def root():
    return {
        "name": "Fleet of Institutes Nexus",
        "version": "0.1.0",
        "docs": "/docs",
        "skill": "/skill",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
