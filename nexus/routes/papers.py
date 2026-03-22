from __future__ import annotations

import base64
import json as _json

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Header, Request

from auth import require_signed
from config import FEDERATION_ENABLED
from database import (
    insert_paper,
    get_paper,
    add_citation,
    add_reaction,
    insert_review,
    get_reviews_for_paper,
    compute_global_id,
)
from models import (
    PaperCreate,
    PaperOut,
    CiteRequest,
    ReactRequest,
    ReactionOut,
    ReviewCreate,
    ReviewOut,
    PaperSummary,
)

router = APIRouter(prefix="/papers", tags=["papers"])


@router.get("/{paper_id}", response_model=PaperOut)
async def read_paper(paper_id: str, request: Request):
    conn = request.app.state.db
    paper = get_paper(conn, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    if not paper.get("content_cached", True) and FEDERATION_ENABLED:
        from federation import fetch_paper_content
        fetched = await fetch_paper_content(conn, paper)
        if fetched:
            paper = fetched

    return paper


@router.post("", response_model=PaperOut, status_code=201)
async def publish_paper(
    body: PaperCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    institute: dict = Depends(require_signed),
    x_signature: str = Header(""),
    x_public_key: str = Header(""),
    x_timestamp: str = Header(""),
):
    conn = request.app.state.db

    if body.supersedes and body.retracts:
        raise HTTPException(status_code=400, detail="A paper cannot both supersede and retract another paper")

    if body.supersedes:
        prev = get_paper(conn, body.supersedes)
        if not prev:
            raise HTTPException(status_code=404, detail="Superseded paper not found")
        if prev["institute_id"] != institute["id"]:
            raise HTTPException(status_code=403, detail="Can only supersede your own papers")
        if prev.get("superseded_by"):
            raise HTTPException(status_code=409, detail="Paper has already been superseded")

    if body.retracts:
        original = get_paper(conn, body.retracts)
        if not original:
            raise HTTPException(status_code=404, detail="Retracted paper not found")
        if original["institute_id"] != institute["id"]:
            raise HTTPException(status_code=403, detail="Can only retract your own papers")
        if original.get("retracted_by"):
            raise HTTPException(status_code=409, detail="Paper has already been retracted")

    ext_refs = _json.dumps([r.model_dump() for r in body.external_references]) if body.external_references else ""

    global_id = compute_global_id(
        institute.get("public_key", ""),
        body.title,
        body.content,
        "",
    )

    paper = insert_paper(
        conn,
        institute_id=institute["id"],
        title=body.title,
        summary=body.summary,
        content=body.content,
        tags=body.tags,
        cited_paper_ids=body.cited_paper_ids,
        supersedes=body.supersedes,
        retracts=body.retracts,
        external_references=ext_refs,
        global_id=global_id,
        origin_nexus=request.app.state.nexus_id,
    )

    from routes.ws import broadcast
    await broadcast("new_paper", PaperSummary(
        id=paper["id"],
        institute_id=paper["institute_id"],
        institute_name=paper.get("institute_name", ""),
        institute_origin_nexus=paper["institute_origin_nexus"],
        title=paper["title"],
        summary=paper["summary"],
        tags=paper["tags"],
        timestamp=paper["timestamp"],
        citation_count=paper.get("citation_count", 0),
        reaction_counts={},
        review_counts={},
    ).model_dump())

    if FEDERATION_ENABLED:
        from federation import build_paper_metadata_envelope, forward_to_peers
        nexus_id = request.app.state.nexus_id
        signing_key = request.app.state.signing_key
        body_bytes = await request.body()
        institute_body_b64 = base64.b64encode(body_bytes).decode()
        envelope = build_paper_metadata_envelope(
            paper, x_public_key, x_signature, x_timestamp, nexus_id,
            institute_body_b64=institute_body_b64,
        )
        background_tasks.add_task(forward_to_peers, conn, envelope, signing_key)

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
    background_tasks: BackgroundTasks,
    institute: dict = Depends(require_signed),
    x_signature: str = Header(""),
    x_public_key: str = Header(""),
    x_timestamp: str = Header(""),
):
    conn = request.app.state.db

    paper = get_paper(conn, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    reaction = add_reaction(conn, paper_id, institute["id"], body.reaction_type)

    from routes.ws import broadcast
    await broadcast("reaction", {**reaction, "paper_id": paper_id})

    if FEDERATION_ENABLED:
        from federation import build_reaction_envelope, forward_to_peers
        nexus_id = request.app.state.nexus_id
        signing_key = request.app.state.signing_key
        body_bytes = await request.body()
        institute_body_b64 = base64.b64encode(body_bytes).decode()
        envelope = build_reaction_envelope(
            reaction, paper_id, paper.get("global_id", ""),
            x_public_key, x_signature, x_timestamp, nexus_id,
            institute_body_b64=institute_body_b64,
        )
        background_tasks.add_task(forward_to_peers, conn, envelope, signing_key)

    return reaction


@router.post("/{paper_id}/review", response_model=ReviewOut, status_code=201)
async def submit_review(
    paper_id: str,
    body: ReviewCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    institute: dict = Depends(require_signed),
    x_signature: str = Header(""),
    x_public_key: str = Header(""),
    x_timestamp: str = Header(""),
):
    conn = request.app.state.db

    paper = get_paper(conn, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    if paper["institute_id"] == institute["id"]:
        raise HTTPException(status_code=403, detail="Cannot review your own paper")

    review = insert_review(
        conn, paper_id, institute["id"],
        summary=body.summary,
        strengths=body.strengths,
        weaknesses=body.weaknesses,
        questions=body.questions,
        recommendation=body.recommendation,
        confidence=body.confidence,
    )

    from routes.ws import broadcast
    await broadcast("new_review", {**review, "paper_id": paper_id})

    if FEDERATION_ENABLED:
        from federation import build_review_envelope, forward_to_peers
        nexus_id = request.app.state.nexus_id
        signing_key = request.app.state.signing_key
        body_bytes = await request.body()
        institute_body_b64 = base64.b64encode(body_bytes).decode()
        envelope = build_review_envelope(
            review, paper.get("global_id", ""),
            x_public_key, x_signature, x_timestamp, nexus_id,
            institute_body_b64=institute_body_b64,
        )
        background_tasks.add_task(forward_to_peers, conn, envelope, signing_key)

    return review


@router.get("/{paper_id}/reviews", response_model=list[ReviewOut])
async def get_paper_reviews(paper_id: str, request: Request):
    conn = request.app.state.db

    paper = get_paper(conn, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    return get_reviews_for_paper(conn, paper_id)
