import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import get_connection, init_db
from routes import institutes, papers, feed, ws


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = _connect_with_retry()
    init_db(conn)
    app.state.db = conn
    yield
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
)

app.include_router(institutes.router)
app.include_router(papers.router)
app.include_router(feed.router)
app.include_router(ws.router)


@app.get("/", tags=["meta"])
async def root():
    return {
        "name": "Fleet of Institutes Nexus",
        "version": "0.1.0",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
