import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey,
    Enum as SAEnum, Text, func
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class LeadSource(str, enum.Enum):
    scanner = "scanner"
    partner = "partner"
    manual = "manual"


class BusinessDomain(str, enum.Enum):
    first = "first"
    second = "second"
    third = "third"


class ColdStage(str, enum.Enum):
    new = "new"
    contacted = "contacted"
    qualified = "qualified"
    transferred = "transferred"
    lost = "lost"


class SaleStage(str, enum.Enum):
    new = "new"
    kyc = "kyc"
    agreement = "agreement"
    paid = "paid"
    lost = "lost"


# Define allowed transitions
COLD_STAGE_TRANSITIONS: dict[ColdStage, list[ColdStage]] = {
    ColdStage.new: [ColdStage.contacted, ColdStage.lost],
    ColdStage.contacted: [ColdStage.qualified, ColdStage.lost],
    ColdStage.qualified: [ColdStage.transferred, ColdStage.lost],
    ColdStage.transferred: [],  # terminal — no transitions
    ColdStage.lost: [],         # terminal
}

SALE_STAGE_TRANSITIONS: dict[SaleStage, list[SaleStage]] = {
    SaleStage.new: [SaleStage.kyc, SaleStage.lost],
    SaleStage.kyc: [SaleStage.agreement, SaleStage.lost],
    SaleStage.agreement: [SaleStage.paid, SaleStage.lost],
    SaleStage.paid: [],   # terminal
    SaleStage.lost: [],   # terminal
}


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(SAEnum(LeadSource), nullable=False)
    stage = Column(SAEnum(ColdStage), nullable=False, default=ColdStage.new)
    business_domain = Column(SAEnum(BusinessDomain), nullable=True)
    message_count = Column(Integer, nullable=False, default=0)

    # AI fields
    ai_score = Column(Float, nullable=True)
    ai_recommendation = Column(String(64), nullable=True)
    ai_reason = Column(Text, nullable=True)
    ai_analyzed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationship
    sale = relationship("Sale", back_populates="lead", uselist=False)


class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False, unique=True)
    stage = Column(SAEnum(SaleStage), nullable=False, default=SaleStage.new)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationship
    lead = relationship("Lead", back_populates="sale")
