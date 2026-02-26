import json
import logging
from typing import Optional

import anthropic

from app.core.config import settings
from app.core.exceptions import AIServiceError
from app.models.lead import Lead
from app.schemas.lead import AIAnalysisResult

logger = logging.getLogger(__name__)

# Minimal data sent to AI — only what's needed for analysis
AI_PROMPT_TEMPLATE = """You are an AI assistant for a CRM system. Analyze the following lead and provide a structured assessment.

Lead data:
- Source: {source}
- Current stage: {stage}
- Business domain: {business_domain}
- Total messages/communications: {message_count}

Based on this data, evaluate:
1. The probability (0.0 to 1.0) of a successful deal
2. A recommendation for the manager (one of: transfer_to_sales, continue_nurturing, mark_as_lost)
3. A brief reason for your assessment

Respond ONLY with a valid JSON object in this exact format:
{{
  "score": <float between 0.0 and 1.0>,
  "recommendation": "<transfer_to_sales|continue_nurturing|mark_as_lost>",
  "reason": "<one sentence explanation>"
}}"""


class AIService:
    """
    Responsible for sending lead data to Claude AI and parsing the response.

    What data is sent to AI:
    - source (where the lead came from)
    - current cold stage
    - business domain (if known)
    - message count (activity level)

    What AI decides:
    - probability score (0–1)
    - recommendation action
    - reasoning

    What AI does NOT decide:
    - whether to actually transfer the lead (that's enforced by business logic)
    - stage transitions (manager controls that)
    """

    def __init__(self):
        if not settings.ANTHROPIC_API_KEY:
            logger.warning("ANTHROPIC_API_KEY is not set — AI service will use mock responses")
        self._client: Optional[anthropic.AsyncAnthropic] = (
            anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            if settings.ANTHROPIC_API_KEY
            else None
        )

    async def analyze_lead(self, lead: Lead) -> AIAnalysisResult:
        """
        Analyze a lead and return AI score + recommendation.
        Falls back to a rule-based mock if API key is not configured.
        """
        if self._client is None:
            return self._mock_analysis(lead)

        prompt = AI_PROMPT_TEMPLATE.format(
            source=lead.source.value,
            stage=lead.stage.value,
            business_domain=lead.business_domain.value if lead.business_domain else "unknown",
            message_count=lead.message_count,
        )

        try:
            message = await self._client.messages.create(
                model=settings.AI_MODEL,
                max_tokens=256,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = message.content[0].text.strip()
            data = json.loads(raw)
            return AIAnalysisResult(**data)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response: {e}")
            raise AIServiceError(f"AI returned invalid JSON: {e}")
        except anthropic.APIError as e:
            logger.error(f"Anthropic API error: {e}")
            raise AIServiceError(f"AI service unavailable: {e}")

    def _mock_analysis(self, lead: Lead) -> AIAnalysisResult:
        """
        Simple rule-based scoring used when AI API key is not configured.
        Useful for development and testing without API costs.
        """
        score = 0.3

        # Activity bonus
        if lead.message_count >= 5:
            score += 0.2
        elif lead.message_count >= 2:
            score += 0.1

        # Business domain bonus
        if lead.business_domain is not None:
            score += 0.2

        # Stage bonus
        stage_bonus = {
            "new": 0.0,
            "contacted": 0.1,
            "qualified": 0.2,
        }
        score += stage_bonus.get(lead.stage.value, 0.0)

        # Source bonus
        if lead.source.value == "partner":
            score += 0.1

        score = min(score, 1.0)

        if score >= 0.6:
            recommendation = "transfer_to_sales"
            reason = "Lead has sufficient activity and domain data to proceed to sales"
        elif score >= 0.4:
            recommendation = "continue_nurturing"
            reason = "Lead shows potential but needs more engagement"
        else:
            recommendation = "mark_as_lost"
            reason = "Low activity and missing domain info — not worth pursuing now"

        return AIAnalysisResult(score=round(score, 2), recommendation=recommendation, reason=reason)


ai_service = AIService()
