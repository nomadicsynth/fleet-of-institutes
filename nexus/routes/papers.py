from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from auth import require_signed
from database import insert_paper, get_paper, add_citation, add_reaction
from models import PaperCreate, PaperOut, CiteRequest, ReactRequest, ReactionOut

router = APIRouter(prefix="/papers", tags=["papers"])


@router.get("/{paper_id}", response_model=PaperOut)
async def read_paper(paper_id: str, request: Request):
    conn = request.app.state.db
    paper = get_paper(conn, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper


@router.post("", response_model=PaperOut, status_code=201)
async def publish_paper(
    body: PaperCreate,
    request: Request,
    institute: dict = Depends(require_signed),
):
    conn = request.app.state.db
    paper = insert_paper(
        conn,
        institute_id=institute["id"],
        title=body.title,
        summary=body.summary,
        content=body.content,
        tags=body.tags,
        cited_paper_ids=body.cited_paper_ids,
    )

    from routes.ws import broadcast
    from models import PaperSummary
    await broadcast("new_paper", PaperSummary(
        id=paper["id"],
        institute_id=paper["institute_id"],
        institute_name=paper.get("institute_name", ""),
        title=paper["title"],
        summary=paper["summary"],
        tags=paper["tags"],
        timestamp=paper["timestamp"],
        citation_count=paper.get("citation_count", 0),
        reaction_counts={},
    ).model_dump())

    return paper


@router.post("/{paper_id}/cite", status_code=201)
async def cite_paper(
    paper_id: str,
    body: CiteRequest,
    request: Request,
    institute: dict = Depends(require_signed),
):
    conn = request.app.state.db

    cited = get_paper(conn, paper_id)
    if not cited:
        raise HTTPException(status_code=404, detail="Cited paper not found")

    citing = get_paper(conn, body.citing_paper_id)
    if not citing:
        raise HTTPException(status_code=404, detail="Citing paper not found")
    if citing["institute_id"] != institute["id"]:
        raise HTTPException(status_code=403, detail="Citing paper does not belong to your institute")

    add_citation(conn, body.citing_paper_id, paper_id)
    return {"status": "cited", "citing": body.citing_paper_id, "cited": paper_id}


@router.post("/{paper_id}/react", response_model=ReactionOut, status_code=201)
async def react_to_paper(
    paper_id: str,
    body: ReactRequest,
    request: Request,
    institute: dict = Depends(require_signed),
):
    conn = request.app.state.db

    paper = get_paper(conn, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    reaction = add_reaction(conn, paper_id, institute["id"], body.reaction_type)

    from routes.ws import broadcast
    await broadcast("reaction", {**reaction, "paper_id": paper_id})

    return reaction
