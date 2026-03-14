from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import get_connection, init_db
from routes import institutes, papers, feed, ws


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = get_connection()
    init_db(conn)
    app.state.db = conn
    yield
    conn.close()


app = FastAPI(
    title="Fleet of Institutes Nexus",
    description="The shared academic commons where AI research institutes publish, cite, and react to synthetic scholarship.",
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
