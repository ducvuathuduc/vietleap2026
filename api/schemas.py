"""Pydantic request/response models (mirrored by web/src/lib/api/types.ts)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class DatasetSummary(BaseModel):
    id: str
    name: str
    domain: str
    rows: int
    target: str
    source_file: str
    created: str | None = None


class Job(BaseModel):
    id: str
    status: Literal["queued", "running", "done", "error"]
    dataset_id: str | None = None
    error: str | None = None
    started: float
    finished: float | None = None


class WhatIfRequest(BaseModel):
    feature: str
    pct_change: float = Field(ge=-90, le=500)
    target: str | None = None


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str = ""
    history: list[ChatMessage] = []
    auto: bool = False
    top_n: int = Field(default=5, ge=1, le=12)


class RowsResponse(BaseModel):
    columns: list[dict[str, Any]]
    rows: list[dict[str, Any]]
    total: int
    page: int
    page_size: int
