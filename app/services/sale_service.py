from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import SaleNotFoundError, InvalidStageTransitionError
from app.models.lead import Sale, SaleStage, SALE_STAGE_TRANSITIONS
from app.schemas.lead import SaleUpdateStage


class SaleService:

    async def get(self, db: AsyncSession, sale_id: int) -> Sale:
        result = await db.execute(select(Sale).where(Sale.id == sale_id))
        sale = result.scalar_one_or_none()
        if sale is None:
            raise SaleNotFoundError(sale_id)
        return sale

    async def get_by_lead(self, db: AsyncSession, lead_id: int) -> Sale:
        result = await db.execute(select(Sale).where(Sale.lead_id == lead_id))
        sale = result.scalar_one_or_none()
        if sale is None:
            raise SaleNotFoundError(lead_id)
        return sale

    async def update_stage(self, db: AsyncSession, sale_id: int, new_stage: SaleStage) -> Sale:
        sale = await self.get(db, sale_id)

        allowed = SALE_STAGE_TRANSITIONS.get(sale.stage, [])
        if new_stage not in allowed:
            raise InvalidStageTransitionError(sale.stage.value, new_stage.value)

        sale.stage = new_stage
        await db.commit()
        await db.refresh(sale)
        return sale

    async def list_all(self, db: AsyncSession, skip: int = 0, limit: int = 50) -> list[Sale]:
        result = await db.execute(select(Sale).offset(skip).limit(limit))
        return list(result.scalars().all())


sale_service = SaleService()
