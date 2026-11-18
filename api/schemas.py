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
    status: Literal["queued", "pipeline", "running", "done", "error"]
    dataset_id: str | None = None
    error: str | None = None
    started: float
    finished: float | None = None


class WhatIfRequest(BaseModel):
    feature: str
    pct_change: float = Field(ge=-90, le=500)
    target: str | None = None


class WhatIfChange(BaseModel):
    feature: str
    pct_change: float = Field(ge=-30, le=30)


class WhatIfScenarioRequest(BaseModel):
    changes: list[WhatIfChange] = Field(min_length=1, max_length=5)
    target: str | None = None


class WhatIfContribution(WhatIfChange):
    target_change_pct: float | None
    ci90_pct: list[float | None] = Field(min_length=2, max_length=2)


class WhatIfScenarioResult(BaseModel):
    changes: list[WhatIfChange]
    target: str
    target_change_pct: float | None
    ci90_pct: list[float | None] = Field(min_length=2, max_length=2)
    target_change_abs: float | None
    baseline_target_mean: float | None
    range_warnings: list[str]
    collinearity_warnings: list[str]
    contributions: list[WhatIfContribution]
    interpretation: str


class SaveScenarioBody(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    request: WhatIfScenarioRequest



class SavedScenario(SaveScenarioBody):
    result: WhatIfScenarioResult


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
