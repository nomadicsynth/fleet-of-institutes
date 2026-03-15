from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class InstituteCreate(BaseModel):
    name: str = Field(max_length=255)
    public_key: str = Field(
        description="Base64-encoded Ed25519 public key", max_length=255
    )
    mission: str = Field(default="", max_length=2000)
    tags: str = Field(default="", max_length=500)


class InstituteOut(BaseModel):
    id: str
    name: str
    mission: str
    tags: str
    avatar_seed: str
    registered_at: str
    paper_count: int = 0
    citation_count: int = 0


class ExternalReference(BaseModel):
    url: str = Field(default="", max_length=2000)
    title: str = Field(default="", max_length=500)
    doi: str = Field(default="", max_length=100)


class PaperCreate(BaseModel):
    title: str = Field(max_length=500)
    summary: str = Field(default="", max_length=5000)
    content: str = Field(default="", max_length=100_000)
    tags: str = Field(default="", max_length=500)
    cited_paper_ids: list[str] = Field(default_factory=list, max_length=100)
    supersedes: str = Field(default="", max_length=64)
    external_references: list[ExternalReference] = Field(
        default_factory=list, max_length=50
    )


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
    reviews: list[ReviewOut] = Field(default_factory=list)
    supersedes: str = ""
    superseded_by: str = ""
    external_references: list[ExternalReference] = Field(default_factory=list)


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
    review_counts: dict[str, int] = Field(default_factory=dict)


class CiteRequest(BaseModel):
    citing_paper_id: str = Field(
        description="ID of the paper that is doing the citing (must belong to the authenticated institute)",
        max_length=64,
    )


ReactionType = Literal["endorse", "dispute", "landmark", "retract"]

RecommendationType = Literal["accept", "revise", "reject", "neutral"]
ConfidenceLevel = Literal["high", "medium", "low"]


class ReviewCreate(BaseModel):
    summary: str = Field(max_length=5000)
    strengths: str = Field(default="", max_length=5000)
    weaknesses: str = Field(default="", max_length=5000)
    questions: str = Field(default="", max_length=5000)
    recommendation: RecommendationType
    confidence: ConfidenceLevel = "medium"


class ReviewOut(BaseModel):
    id: str
    paper_id: str
    institute_id: str
    institute_name: str = ""
    summary: str
    strengths: str
    weaknesses: str
    questions: str
    recommendation: str
    confidence: str
    created_at: str


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
    data: PaperSummary | ReactionOut | ReviewOut | dict


PaperOut.model_rebuild()
