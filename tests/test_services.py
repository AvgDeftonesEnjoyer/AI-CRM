import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.exceptions import (
    LeadNotFoundError, InvalidStageTransitionError, LeadTransferError
)
from app.models.lead import Lead, Sale, ColdStage, SaleStage, LeadSource, BusinessDomain
from app.schemas.lead import AIAnalysisResult
from app.services.ai_service import AIService
from app.services.lead_service import LeadService, TRANSFER_MIN_SCORE


# ─── AI Service Mock Tests ─────────────────────────────────────────────────────

class TestAIServiceMock:
    """Test the rule-based mock AI — no API calls needed."""

    def _make_lead(self, source="partner", stage="qualified", domain=BusinessDomain.first, msgs=5):
        lead = MagicMock(spec=Lead)
        lead.source = MagicMock(value=source)
        lead.stage = MagicMock(value=stage)
        lead.business_domain = domain
        lead.message_count = msgs
        return lead

    def test_high_activity_domain_scores_above_threshold(self):
        svc = AIService()
        lead = self._make_lead(msgs=5, domain=BusinessDomain.first)
        result = svc._mock_analysis(lead)
        assert result.score >= TRANSFER_MIN_SCORE

    def test_no_domain_low_activity_scores_below_threshold(self):
        svc = AIService()
        lead = self._make_lead(msgs=0, domain=None, stage="new", source="manual")
        result = svc._mock_analysis(lead)
        assert result.score < TRANSFER_MIN_SCORE

    def test_result_has_all_fields(self):
        svc = AIService()
        lead = self._make_lead()
        result = svc._mock_analysis(lead)
        assert 0.0 <= result.score <= 1.0
        assert result.recommendation in ("transfer_to_sales", "continue_nurturing", "mark_as_lost")
        assert len(result.reason) > 0


# ─── Stage Transition Tests ───────────────────────────────────────────────────

class TestColdStageTransitions:
    from app.models.lead import COLD_STAGE_TRANSITIONS

    def test_new_can_go_to_contacted(self):
        from app.models.lead import COLD_STAGE_TRANSITIONS, ColdStage
        assert ColdStage.contacted in COLD_STAGE_TRANSITIONS[ColdStage.new]

    def test_transferred_is_terminal(self):
        from app.models.lead import COLD_STAGE_TRANSITIONS, ColdStage
        assert COLD_STAGE_TRANSITIONS[ColdStage.transferred] == []

    def test_lost_is_terminal(self):
        from app.models.lead import COLD_STAGE_TRANSITIONS, ColdStage
        assert COLD_STAGE_TRANSITIONS[ColdStage.lost] == []

    def test_cannot_skip_from_new_to_qualified(self):
        from app.models.lead import COLD_STAGE_TRANSITIONS, ColdStage
        assert ColdStage.qualified not in COLD_STAGE_TRANSITIONS[ColdStage.new]


class TestSaleStageTransitions:
    def test_paid_is_terminal(self):
        from app.models.lead import SALE_STAGE_TRANSITIONS, SaleStage
        assert SALE_STAGE_TRANSITIONS[SaleStage.paid] == []

    def test_new_goes_to_kyc(self):
        from app.models.lead import SALE_STAGE_TRANSITIONS, SaleStage
        assert SaleStage.kyc in SALE_STAGE_TRANSITIONS[SaleStage.new]


# ─── Transfer Rules Tests ─────────────────────────────────────────────────────

class TestTransferRules:
    """Verify transfer business rules are enforced correctly."""

    def _make_qualified_lead(self, score=0.75, domain=BusinessDomain.first):
        lead = MagicMock(spec=Lead)
        lead.id = 1
        lead.stage = ColdStage.qualified
        lead.ai_score = score
        lead.business_domain = domain
        lead.sale = None
        return lead

    @pytest.mark.asyncio
    async def test_transfer_succeeds_when_all_conditions_met(self):
        svc = LeadService()
        lead = self._make_qualified_lead(score=0.75)

        db = AsyncMock()
        svc.get = AsyncMock(return_value=lead)
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        result = await svc.transfer_to_sales(db, lead_id=1)
        assert lead.stage == ColdStage.transferred

    @pytest.mark.asyncio
    async def test_transfer_fails_if_score_too_low(self):
        svc = LeadService()
        lead = self._make_qualified_lead(score=0.4)
        db = AsyncMock()
        svc.get = AsyncMock(return_value=lead)

        with pytest.raises(LeadTransferError, match="score"):
            await svc.transfer_to_sales(db, lead_id=1)

    @pytest.mark.asyncio
    async def test_transfer_fails_if_no_domain(self):
        svc = LeadService()
        lead = self._make_qualified_lead(score=0.8, domain=None)
        db = AsyncMock()
        svc.get = AsyncMock(return_value=lead)

        with pytest.raises(LeadTransferError, match="domain"):
            await svc.transfer_to_sales(db, lead_id=1)

    @pytest.mark.asyncio
    async def test_transfer_fails_if_not_qualified(self):
        svc = LeadService()
        lead = self._make_qualified_lead(score=0.8)
        lead.stage = ColdStage.contacted  # not qualified
        db = AsyncMock()
        svc.get = AsyncMock(return_value=lead)

        with pytest.raises(LeadTransferError, match="qualified"):
            await svc.transfer_to_sales(db, lead_id=1)

    @pytest.mark.asyncio
    async def test_transfer_fails_if_no_ai_score(self):
        svc = LeadService()
        lead = self._make_qualified_lead(score=None)
        db = AsyncMock()
        svc.get = AsyncMock(return_value=lead)

        with pytest.raises(LeadTransferError, match="AI"):
            await svc.transfer_to_sales(db, lead_id=1)
