from __future__ import annotations

from fastapi import APIRouter, Query, Request

from config import MAX_PAGE
from database import get_feed, get_trending
from models import FeedResponse, PaperSummary

router = APIRouter(tags=["feed"])


@router.get("/feed", response_model=FeedResponse)
async def browse_feed(
    request: Request,
    tag: str | None = Query(None),
    institute: str | None = Query(None),
    since: str | None = Query(None),
    sort: str = Query("recent", pattern="^(recent|cited)$"),
    page: int = Query(1, ge=1, le=MAX_PAGE),
    page_size: int = Query(20, ge=1, le=100),
):
    conn = request.app.state.db
    papers, total = get_feed(
        conn, tag=tag, institute=institute, since=since, sort=sort,
        page=page, page_size=page_size,
    )
    return FeedResponse(
        papers=[PaperSummary(**p) for p in papers],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/feed/trending", response_model=list[PaperSummary])
async def trending_papers(
    request: Request,
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(20, ge=1, le=100),
):
    conn = request.app.state.db
    papers = get_trending(conn, hours=hours, limit=limit)
    return [PaperSummary(**p) for p in papers]
