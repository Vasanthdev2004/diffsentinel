from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Issue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    line_number: int = Field(ge=1)
    severity: Literal["CRITICAL", "WARNING"]
    category: Literal[
        "BLOCKING_IO",
        "MISSING_AWAIT",
        "COMPLEXITY_REGRESSION",
        "UNNECESSARY_CLONE",
        "INEFFICIENT_COLLECTION",
    ]
    explanation: str
    impact: str
    optimized_code: str
    confidence: float = Field(ge=0.0, le=1.0)


class AnalysisResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issues: list[Issue]
