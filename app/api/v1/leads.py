from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import (
    LeadNotFoundError, InvalidStageTransitionError,
    LeadTransferError, AIServiceError
)
from app.schemas.lead import (
    LeadCreate, LeadUpdateStage, LeadResponse,
    LeadWithSaleResponse, SaleResponse
)
from app.models.user import User
from app.services.lead_service import lead_service

from app.api.deps import get_current_user
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/leads", tags=["Leads"])


@router.post("/", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
async def create_lead(
    data: LeadCreate, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new lead."""
    lead = await lead_service.create(db, data)
    return lead


@router.get("/", response_model=list[LeadWithSaleResponse])
async def list_leads(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all leads with pagination."""
    return await lead_service.list_all(db, skip=skip, limit=limit)


@router.get("/{lead_id}", response_model=LeadWithSaleResponse)
async def get_lead(
    lead_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a single lead by ID."""
    try:
        return await lead_service.get(db, lead_id)
    except LeadNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{lead_id}/stage", response_model=LeadResponse)
async def update_lead_stage(
    lead_id: int,
    body: LeadUpdateStage,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Transition lead to a new stage.
    Enforces valid transitions and blocks changes to terminal stages.
    """
    try:
        return await lead_service.update_stage(db, lead_id, body.stage)
    except LeadNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidStageTransitionError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/{lead_id}/messages", response_model=LeadResponse)
async def increment_messages(
    lead_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Register a new communication with the lead (increments message count)."""
    try:
        return await lead_service.increment_messages(db, lead_id)
    except LeadNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{lead_id}/analyze", response_model=LeadResponse)
@limiter.limit("10/minute")
async def analyze_lead(
    request: Request,
    lead_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Request AI analysis for this lead.
    Saves score, recommendation and reason to the lead record.
    The manager uses this data to decide whether to transfer.
    """
    try:
        return await lead_service.analyze_with_ai(db, lead_id)
    except LeadNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except AIServiceError as e:
        raise HTTPException(status_code=503, detail=f"AI service error: {e}")


@router.post("/{lead_id}/transfer", response_model=SaleResponse, status_code=status.HTTP_201_CREATED)
async def transfer_lead_to_sales(
    lead_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Transfer a qualified lead to sales pipeline.

    Requirements (enforced by system, NOT by AI):
    - Lead stage must be 'qualified'
    - AI score >= 0.6
    - Business domain must be set
    """
    try:
        return await lead_service.transfer_to_sales(db, lead_id)
    except LeadNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except LeadTransferError as e:
        raise HTTPException(status_code=422, detail=str(e))
