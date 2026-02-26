from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict

from app.models.lead import LeadSource, BusinessDomain, ColdStage, SaleStage


# ─── AI ───────────────────────────────────────────────────────────────────────

class AIAnalysisResult(BaseModel):
    score: float = Field(..., ge=0.0, le=1.0, description="Probability of successful deal")
    recommendation: str = Field(..., description="Action recommendation for manager")
    reason: str = Field(..., description="Explanation of the AI decision")


# ─── Lead ─────────────────────────────────────────────────────────────────────

class LeadCreate(BaseModel):
    source: LeadSource
    business_domain: Optional[BusinessDomain] = None


class LeadUpdateStage(BaseModel):
    stage: ColdStage


class LeadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: LeadSource
    stage: ColdStage
    business_domain: Optional[BusinessDomain]
    message_count: int

    # AI fields
    ai_score: Optional[float]
    ai_recommendation: Optional[str]
    ai_reason: Optional[str]
    ai_analyzed_at: Optional[datetime]

    created_at: datetime
    updated_at: datetime


class LeadWithSaleResponse(LeadResponse):
    sale: Optional["SaleResponse"] = None


# ─── Sale ─────────────────────────────────────────────────────────────────────

class SaleUpdateStage(BaseModel):
    stage: SaleStage


class SaleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lead_id: int
    stage: SaleStage
    created_at: datetime
    updated_at: datetime


LeadWithSaleResponse.model_rebuild()
