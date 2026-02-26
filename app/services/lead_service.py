from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import (
    LeadNotFoundError, InvalidStageTransitionError, LeadTransferError
)
from app.models.lead import Lead, Sale, ColdStage, COLD_STAGE_TRANSITIONS
from app.schemas.lead import LeadCreate, AIAnalysisResult
from app.services.ai_service import ai_service

# Minimum AI score to allow transfer to sales
TRANSFER_MIN_SCORE = 0.6


class LeadService:

    async def create(self, db: AsyncSession, data: LeadCreate) -> Lead:
        lead = Lead(
            source=data.source,
            business_domain=data.business_domain,
            stage=ColdStage.new,
            message_count=0,
        )
        db.add(lead)
        await db.commit()
        await db.refresh(lead)
        return lead

    async def get(self, db: AsyncSession, lead_id: int) -> Lead:
        result = await db.execute(
            select(Lead).where(Lead.id == lead_id).options(selectinload(Lead.sale))
        )
        lead = result.scalar_one_or_none()
        if lead is None:
            raise LeadNotFoundError(lead_id)
        return lead

    async def list_all(self, db: AsyncSession, skip: int = 0, limit: int = 50) -> list[Lead]:
        result = await db.execute(
            select(Lead).options(selectinload(Lead.sale)).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def update_stage(self, db: AsyncSession, lead_id: int, new_stage: ColdStage) -> Lead:
        lead = await self.get(db, lead_id)

        allowed = COLD_STAGE_TRANSITIONS.get(lead.stage, [])
        if new_stage not in allowed:
            raise InvalidStageTransitionError(lead.stage.value, new_stage.value)

        lead.stage = new_stage
        await db.commit()
        await db.refresh(lead)
        return lead

    async def increment_messages(self, db: AsyncSession, lead_id: int) -> Lead:
        """Increment message count to track activity level."""
        lead = await self.get(db, lead_id)
        lead.message_count += 1
        await db.commit()
        await db.refresh(lead)
        return lead

    async def analyze_with_ai(self, db: AsyncSession, lead_id: int) -> Lead:
        """
        Request AI analysis for this lead and persist the result.
        The manager still decides what to do with the recommendation.
        """
        lead = await self.get(db, lead_id)
        result: AIAnalysisResult = await ai_service.analyze_lead(lead)

        lead.ai_score = result.score
        lead.ai_recommendation = result.recommendation
        lead.ai_reason = result.reason
        lead.ai_analyzed_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(lead)
        return lead

    async def transfer_to_sales(self, db: AsyncSession, lead_id: int) -> Sale:
        """
        Transfer a lead to sales.

        Business rules enforced here (NOT by AI):
          1. Lead must be in 'qualified' stage
          2. AI score must be >= 0.6
          3. Lead must have a business_domain set

        AI only provides a recommendation — the decision is enforced here in code.
        """
        lead = await self.get(db, lead_id)

        # Rule 1: stage check
        if lead.stage != ColdStage.qualified:
            raise LeadTransferError(
                f"Lead must be in 'qualified' stage to transfer (current: {lead.stage.value})"
            )

        # Rule 2: AI score check
        if lead.ai_score is None:
            raise LeadTransferError("Lead has not been analyzed by AI yet. Run AI analysis first.")
        if lead.ai_score < TRANSFER_MIN_SCORE:
            raise LeadTransferError(
                f"AI score {lead.ai_score:.2f} is below minimum required {TRANSFER_MIN_SCORE}"
            )

        # Rule 3: business domain check
        if lead.business_domain is None:
            raise LeadTransferError("Lead must have a business_domain set before transfer")

        # Execute transfer
        lead.stage = ColdStage.transferred

        sale = Sale(lead_id=lead.id)
        db.add(sale)

        await db.commit()
        await db.refresh(sale)
        return sale


lead_service = LeadService()
