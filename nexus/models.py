from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class InstituteCreate(BaseModel):
    name: str
    public_key: str = Field(description="Base64-encoded Ed25519 public key")
    mission: str = ""
    tags: str = ""


class InstituteOut(BaseModel):
    id: str
    name: str
    mission: str
    tags: str
    avatar_seed: str
    registered_at: str
    paper_count: int = 0
    citation_count: int = 0


class PaperCreate(BaseModel):
    title: str
    summary: str = ""
    content: str = ""
    tags: str = ""
    cited_paper_ids: list[str] = Field(default_factory=list)


class PaperOut(BaseModel):
    id: str
    institute_id: str
    institute_name: str = ""
    title: str
    summary: str
    content: str
    tags: str
    timestamp: str
    citation_count: int = 0
    citations_outgoing: list[str] = Field(default_factory=list)
    citations_incoming: list[str] = Field(default_factory=list)
    reactions: list[ReactionOut] = Field(default_factory=list)


class PaperSummary(BaseModel):
    id: str
    institute_id: str
    institute_name: str = ""
    title: str
    summary: str
    tags: str
    timestamp: str
    citation_count: int = 0
    reaction_counts: dict[str, int] = Field(default_factory=dict)


class CiteRequest(BaseModel):
    citing_paper_id: str = Field(description="ID of the paper that is doing the citing (must belong to the authenticated institute)")


ReactionType = Literal["endorse", "dispute", "landmark", "retract"]


class ReactRequest(BaseModel):
    reaction_type: ReactionType


class ReactionOut(BaseModel):
    institute_id: str
    institute_name: str = ""
    reaction_type: str
    created_at: str


class FeedResponse(BaseModel):
    papers: list[PaperSummary]
    total: int
    page: int
    page_size: int


class WSEvent(BaseModel):
    event: str
    data: PaperSummary | ReactionOut | dict


PaperOut.model_rebuild()
