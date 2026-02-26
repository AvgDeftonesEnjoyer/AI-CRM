from fastapi import APIRouter

from app.api.v1.leads import router as leads_router
from app.api.v1.sales import router as sales_router
from app.api.v1.auth import router as auth_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(leads_router)
api_router.include_router(sales_router)
