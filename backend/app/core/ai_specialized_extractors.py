"""
AI-Native Specialized Extractors

This module provides AI-driven extraction for complex lease clauses without patterns.
Each extractor uses GPT-4's understanding to extract information intelligently.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import json
import openai
import os
from app.utils.logger import logger


@dataclass
class ExtractionResult:
    """Standard result format for all extractors"""
    extracted_data: Dict[str, Any]
    confidence: float
    warnings: List[str] = None
    calculation_details: Optional[Dict[str, Any]] = None
    ai_reasoning: Optional[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class AISpecializedExtractor:
    """Base class for AI-native specialized extraction"""
    
    def __init__(self):
        self.api_key = os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not found")
        self.client = openai.OpenAI(api_key=self.api_key)
    
    async def _call_gpt(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Call GPT-4 and return parsed JSON response"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
                max_tokens=4000
            )
            
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"GPT call failed: {e}")
            raise


class AIFinancialClauseExtractor(AISpecializedExtractor):
    """
    AI-driven extractor for financial clauses - no patterns, pure understanding
    """
    
    async def extract_base_rent(self, text: str) -> ExtractionResult:
        """AI extracts base rent information"""
        
        system_prompt = """You are a commercial real estate financial analyst.
Extract ALL base rent information from the text.
Don't use patterns - UNDERSTAND the financial terms."""

        user_prompt = f"""Extract base rent details from this lease text:

{text}

Provide comprehensive extraction:
{{
    "base_rent_amount": "exact amount if stated",
    "payment_frequency": "how often paid",
    "rent_type": "gross/net/triple-net/modified-gross",
    "rent_structure": "fixed/variable/percentage",
    "escalations": [
        {{
            "type": "percentage/fixed/cpi/market",
            "amount": "specific amount or percentage",
            "frequency": "when it happens",
            "first_escalation": "when first applied",
            "compounding": "simple/compound"
        }}
    ],
    "free_rent_periods": [
        {{
            "duration": "length of free rent",
            "timing": "when it occurs",
            "conditions": "any conditions"
        }}
    ],
    "additional_rent": "any additional rent components",
    "rent_commencement": "when rent starts",
    "proration": "how partial months handled",
    "late_fees": "penalties for late payment",
    "implicit_terms": "what's implied but not stated",
    "calculations_needed": "any math to determine total rent",
    "confidence": 0.0-1.0,
    "reasoning": "explain your extraction"
}}"""

        result = await self._call_gpt(system_prompt, user_prompt)
        
        return ExtractionResult(
            extracted_data=result,
            confidence=result.get("confidence", 0.5),
            warnings=result.get("warnings", []),
            ai_reasoning=result.get("reasoning", "")
        )
    
    async def extract_percentage_rent(self, text: str) -> ExtractionResult:
        """AI extracts percentage rent with all complexities"""
        
        system_prompt = """You are an expert in retail lease percentage rent.
Understand all aspects of percentage rent clauses."""

        user_prompt = f"""Analyze percentage rent in this text:

{text}

Extract comprehensively:
{{
    "has_percentage_rent": boolean,
    "base_percentage": "base rate if any",
    "natural_breakpoint": "calculated or stated",
    "artificial_breakpoints": [
        {{
            "threshold": "sales level",
            "rate": "percentage above threshold"
        }}
    ],
    "gross_sales_definition": {{
        "included": ["what counts as gross sales"],
        "excluded": ["what's excluded"],
        "special_provisions": ["unique inclusions/exclusions"]
    }},
    "reporting_requirements": {{
        "frequency": "how often reported",
        "deadline": "when due",
        "audit_rights": "landlord's audit provisions"
    }},
    "percentage_rent_offset": "credits against percentage rent",
    "radius_restriction": "competition restrictions",
    "opening_covenant": "required operating hours/days",
    "calculation_example": "show sample calculation if possible",
    "implicit_obligations": "unstated but implied requirements",
    "confidence": 0.0-1.0,
    "reasoning": "explain the extraction"
}}"""

        result = await self._call_gpt(system_prompt, user_prompt)
        
        return ExtractionResult(
            extracted_data=result,
            confidence=result.get("confidence", 0.5),
            ai_reasoning=result.get("reasoning", "")
        )
    
    async def extract_operating_expenses(self, text: str) -> ExtractionResult:
        """AI understands all operating expense provisions"""
        
        system_prompt = """You are an expert in commercial lease operating expenses.
Understand CAM, taxes, insurance, and all expense provisions deeply."""

        user_prompt = f"""Analyze operating expenses in this text:

{text}

Extract complete expense structure:
{{
    "expense_structure": "pro-rata/fixed/base-year/expense-stop",
    "tenant_share": {{
        "calculation_method": "how calculated",
        "percentage": "if stated",
        "denominator": "building/project/phase"
    }},
    "included_expenses": [
        {{
            "category": "type of expense",
            "description": "what's included",
            "caps_or_limits": "any restrictions"
        }}
    ],
    "excluded_expenses": [
        {{
            "category": "type of expense",
            "description": "what's excluded",
            "reason": "why excluded if stated"
        }}
    ],
    "base_year": {{
        "year": "if base year structure",
        "gross_up": "occupancy gross-up provisions",
        "exclusions": "items excluded from base"
    }},
    "expense_caps": {{
        "type": "cumulative/non-cumulative/none",
        "percentage": "cap percentage",
        "carryover": "can unused cap carry forward"
    }},
    "controllable_vs_uncontrollable": {{
        "definition": "how defined",
        "different_treatment": "different caps or rules"
    }},
    "audit_rights": {{
        "tenant_audit": "tenant's right to audit",
        "time_limit": "deadline to object",
        "cost_sharing": "who pays for audit"
    }},
    "reconciliation": {{
        "frequency": "annual/quarterly",
        "timing": "when provided",
        "true_up": "how handled"
    }},
    "special_assessments": "how handled",
    "management_fee": "included and at what rate",
    "hidden_costs": "costs implied but not explicit",
    "total_exposure": "rough calculation of tenant's exposure",
    "confidence": 0.0-1.0,
    "reasoning": "explain the analysis"
}}"""

        result = await self._call_gpt(system_prompt, user_prompt)
        
        return ExtractionResult(
            extracted_data=result,
            confidence=result.get("confidence", 0.5),
            calculation_details=result.get("total_exposure"),
            ai_reasoning=result.get("reasoning", "")
        )


class AIDateTimeExtractor(AISpecializedExtractor):
    """
    AI-driven extraction of dates and time-based provisions
    """
    
    async def extract_critical_dates(self, text: str) -> ExtractionResult:
        """AI extracts all critical dates and deadlines"""
        
        system_prompt = """You are an expert at understanding time-based lease provisions.
Extract ALL dates, deadlines, and time-sensitive obligations."""

        user_prompt = f"""Extract all critical dates and time provisions from:

{text}

Provide comprehensive timeline:
{{
    "key_dates": {{
        "execution_date": "when lease signed",
        "lease_commencement": "when lease starts",
        "rent_commencement": "when rent starts",
        "lease_expiration": "when lease ends",
        "possession_date": "when tenant gets keys"
    }},
    "notice_requirements": [
        {{
            "type": "what notice for",
            "deadline": "specific date or relative timing",
            "method": "how notice given",
            "consequences": "what happens if missed"
        }}
    ],
    "option_deadlines": [
        {{
            "option_type": "renewal/expansion/termination",
            "notice_deadline": "when notice due",
            "exercise_deadline": "when must exercise",
            "blackout_periods": "when can't exercise"
        }}
    ],
    "critical_periods": [
        {{
            "period_type": "fixturing/free-rent/etc",
            "start": "when begins",
            "duration": "how long",
            "conditions": "what triggers or ends it"
        }}
    ],
    "recurring_deadlines": [
        {{
            "type": "what's due",
            "frequency": "how often",
            "specific_date": "day of month/year",
            "grace_period": "if any"
        }}
    ],
    "milestone_dates": [
        {{
            "milestone": "what must happen",
            "deadline": "by when",
            "responsible_party": "who must perform",
            "failure_consequence": "what if missed"
        }}
    ],
    "time_essence": "is time of the essence",
    "date_calculation_methods": "how dates calculated",
    "business_days_definition": "what counts as business day",
    "implicit_deadlines": "deadlines implied but not stated",
    "date_conflicts": "any conflicting dates found",
    "confidence": 0.0-1.0,
    "reasoning": "explain the extraction"
}}"""

        result = await self._call_gpt(system_prompt, user_prompt)
        
        return ExtractionResult(
            extracted_data=result,
            confidence=result.get("confidence", 0.5),
            warnings=result.get("date_conflicts", []),
            ai_reasoning=result.get("reasoning", "")
        )


class AIConditionalClauseExtractor(AISpecializedExtractor):
    """
    AI-driven extraction of conditional provisions and triggers
    """
    
    async def extract_conditional_rights(self, text: str) -> ExtractionResult:
        """AI understands all conditional provisions"""
        
        system_prompt = """You are an expert at understanding conditional legal provisions.
Identify ALL conditions, triggers, and contingencies in lease language."""

        user_prompt = f"""Analyze all conditional provisions in:

{text}

Extract complete conditional structure:
{{
    "conditional_rights": [
        {{
            "right_description": "what right exists",
            "condition_precedent": "what must happen first",
            "condition_subsequent": "what maintains the right",
            "trigger_event": "what activates it",
            "time_limit": "deadline to exercise",
            "notice_requirement": "notice needed"
        }}
    ],
    "triggering_events": [
        {{
            "event_type": "category of trigger",
            "specific_trigger": "exact trigger description",
            "consequences": ["what happens when triggered"],
            "cure_rights": "can it be cured",
            "automatic_vs_optional": "automatic or requires action"
        }}
    ],
    "if_then_provisions": [
        {{
            "condition": "the 'if' part",
            "consequence": "the 'then' part",
            "exceptions": "when it doesn't apply",
            "related_provisions": "other affected sections"
        }}
    ],
    "contingencies": [
        {{
            "contingency_type": "what's contingent",
            "dependent_on": "what it depends on",
            "deadline": "must occur by when",
            "failure_result": "what if contingency fails"
        }}
    ],
    "co_tenancy_provisions": {{
        "has_co_tenancy": boolean,
        "opening_requirements": "for store opening",
        "ongoing_requirements": "to maintain",
        "named_tenants": ["specific tenants required"],
        "occupancy_thresholds": "percentage required",
        "remedies": [
            {{
                "trigger": "what triggers remedy",
                "remedy_type": "rent reduction/termination",
                "remedy_details": "specific terms",
                "landlord_cure_period": "time to fix"
            }}
        ]
    }},
    "go_dark_provisions": {{
        "can_go_dark": boolean,
        "conditions": "when allowed",
        "notice_required": "advance notice",
        "rent_obligation": "continues or modified"
    }},
    "implicit_conditions": "conditions implied but not stated",
    "circular_dependencies": "conditions that depend on each other",
    "ambiguous_triggers": "unclear triggering events",
    "confidence": 0.0-1.0,
    "reasoning": "explain the analysis"
}}"""

        result = await self._call_gpt(system_prompt, user_prompt)
        
        return ExtractionResult(
            extracted_data=result,
            confidence=result.get("confidence", 0.5),
            warnings=result.get("ambiguous_triggers", []),
            ai_reasoning=result.get("reasoning", "")
        )


class AIRightsAndOptionsExtractor(AISpecializedExtractor):
    """
    AI-driven extraction of rights, options, and special provisions
    """
    
    async def extract_all_options(self, text: str) -> ExtractionResult:
        """AI extracts all options and special rights"""
        
        system_prompt = """You are an expert in commercial lease options and special rights.
Understand all types of options, rights, and special provisions deeply."""

        user_prompt = f"""Extract all options and special rights from:

{text}

Provide comprehensive analysis:
{{
    "renewal_options": [
        {{
            "option_number": "which renewal option",
            "term_length": "duration if exercised",
            "notice_deadline": "when notice due",
            "notice_method": "how to notify",
            "rent_determination": {{
                "method": "fixed/market/formula",
                "specifics": "exact terms",
                "dispute_resolution": "if parties disagree"
            }},
            "conditions": "must be met to exercise",
            "blackout_periods": "when can't exercise"
        }}
    ],
    "expansion_rights": {{
        "has_expansion": boolean,
        "type": "ROFR/ROFO/option/must-take",
        "space_description": "what space covered",
        "timing": "when available",
        "pricing": "how priced",
        "combining_space": "can combine with existing"
    }},
    "contraction_rights": {{
        "can_contract": boolean,
        "minimum_retained": "must keep how much",
        "notice_period": "advance notice",
        "fees": "termination fees",
        "timing_restrictions": "when can contract"
    }},
    "termination_options": {{
        "early_termination": boolean,
        "exercisable_when": "specific dates/periods",
        "termination_fee": "payment required",
        "notice_requirements": "how much notice",
        "conditions": "what triggers right"
    }},
    "purchase_options": {{
        "has_option": boolean,
        "option_type": "fixed price/ROFR/ROFO",
        "price_determination": "how calculated",
        "exercise_period": "when can exercise",
        "closing_terms": "key conditions"
    }},
    "special_rights": [
        {{
            "right_type": "what kind of right",
            "description": "detailed description",
            "conditions": "when applicable",
            "value": "economic value if any"
        }}
    ],
    "exclusive_rights": {{
        "exclusivity_granted": boolean,
        "scope": "what's exclusive",
        "radius": "geographic limit",
        "exceptions": "carve-outs",
        "remedies": "if violated"
    }},
    "assignment_subletting": {{
        "permitted": "yes/no/conditional",
        "landlord_consent": "required/not required",
        "consent_standard": "reasonable/sole discretion",
        "profit_sharing": "excess rent provisions",
        "recapture_right": "can landlord take back",
        "permitted_transfers": "transfers without consent"
    }},
    "hidden_options": "options implied but not explicit",
    "option_interactions": "how options affect each other",
    "strategic_value": "business value of options",
    "confidence": 0.0-1.0,
    "reasoning": "explain the analysis"
}}"""

        result = await self._call_gpt(system_prompt, user_prompt)
        
        return ExtractionResult(
            extracted_data=result,
            confidence=result.get("confidence", 0.5),
            ai_reasoning=result.get("reasoning", "")
        )


def create_specialized_extractor(clause_type: str):
    """Factory function to create appropriate AI-native specialized extractor"""
    extractors = {
        "financial": AIFinancialClauseExtractor(),
        "datetime": AIDateTimeExtractor(),
        "conditional": AIConditionalClauseExtractor(),
        "rights": AIRightsAndOptionsExtractor()
    }
    
    return extractors.get(clause_type)


# Wrapper classes for backward compatibility
class FinancialClauseExtractor(AIFinancialClauseExtractor):
    """Backward compatible wrapper"""
    pass

class DateTimeExtractor(AIDateTimeExtractor):
    """Backward compatible wrapper"""
    pass

class ConditionalClauseExtractor(AIConditionalClauseExtractor):
    """Backward compatible wrapper"""
    pass

class RightsAndOptionsExtractor(AIRightsAndOptionsExtractor):
    """Backward compatible wrapper"""
    pass
