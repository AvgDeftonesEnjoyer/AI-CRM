from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import SaleNotFoundError, InvalidStageTransitionError
from app.schemas.lead import SaleUpdateStage, SaleResponse
from app.models.user import User
from app.services.sale_service import sale_service

from app.api.deps import get_current_user

router = APIRouter(prefix="/sales", tags=["Sales"])


@router.get("/", response_model=list[SaleResponse])
async def list_sales(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all sales."""
    return await sale_service.list_all(db, skip=skip, limit=limit)


@router.get("/{sale_id}", response_model=SaleResponse)
async def get_sale(
    sale_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a single sale by ID."""
    try:
        return await sale_service.get(db, sale_id)
    except SaleNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{sale_id}/stage", response_model=SaleResponse)
async def update_sale_stage(
    sale_id: int,
    body: SaleUpdateStage,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Transition a sale to a new stage.
    Enforces valid transitions and blocks changes to 'paid' (terminal).
    """
    try:
        return await sale_service.update_stage(db, sale_id, body.stage)
    except SaleNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidStageTransitionError as e:
        raise HTTPException(status_code=422, detail=str(e))
