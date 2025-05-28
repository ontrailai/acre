"""
Specialized Extractors for Complex Real Estate Clauses

This module contains specialized extractors for different types of complex
clauses commonly found in real estate documents.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import re
import json
from decimal import Decimal
from app.utils.logger import logger


@dataclass
class ExtractionResult:
    """Standard result format for all extractors"""
    extracted_data: Dict[str, Any]
    confidence: float
    warnings: List[str] = None
    calculation_details: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class FinancialClauseExtractor:
    """
    Specialized extractor for financial clauses including:
    - Base rent and escalations
    - Percentage rent with breakpoints
    - CAM charges and reconciliations
    - Security deposits
    - Late fees and interest
    """
    
    def __init__(self):
        self.currency_pattern = r'\$[\d,]+(?:\.\d{2})?'
        self.percentage_pattern = r'(\d+(?:\.\d+)?)\s*%'
        self.psf_pattern = r'\$[\d,]+(?:\.\d{2})?\s*(?:per|psf|/sf|per\s+square\s+foot)'
        
    def extract_base_rent(self, text: str) -> ExtractionResult:
        """Extract base rent information including escalations"""
        data = {
            "base_rent_amount": None,
            "payment_frequency": None,
            "rent_type": None,  # gross, net, triple net
            "escalations": [],
            "free_rent_periods": []
        }
        warnings = []
        
        # Extract base rent amount
        rent_patterns = [
            (r'base\s+rent\s+(?:of\s+)?(' + self.currency_pattern + r')\s*per\s*month', 'monthly'),
            (r'monthly\s+rent\s+(?:of\s+)?(' + self.currency_pattern + ')', 'monthly'),
            (r'annual\s+rent\s+(?:of\s+)?(' + self.currency_pattern + ')', 'annual'),
            (r'(' + self.currency_pattern + r')\s*per\s*(?:calendar\s*)?month', 'monthly')
        ]
        
        for pattern, frequency in rent_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data["base_rent_amount"] = self._parse_currency(match.group(1))
                data["payment_frequency"] = frequency
                break
                
        # Check for PSF rent
        psf_match = re.search(self.psf_pattern, text, re.IGNORECASE)
        if psf_match:
            data["rent_type"] = "per_square_foot"
            
        # Extract escalations
        escalation_patterns = [
            r'(?:increase|escalat\w+).*?(\d+(?:\.\d+)?)\s*%\s*(?:per\s*)?(?:year|annual)',
            r'(\d+(?:\.\d+)?)\s*%\s*annual\s*(?:increase|escalation)',
            r'(?:cpi|consumer\s*price\s*index).*?(?:increase|adjustment)'
        ]
        
        for pattern in escalation_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                if match.groups():
                    escalation = {
                        "type": "percentage",
                        "amount": float(match.group(1)) if match.group(1) else None,
                        "frequency": "annual"
                    }
                else:
                    escalation = {
                        "type": "cpi",
                        "frequency": "annual"
                    }
                data["escalations"].append(escalation)
                
        # Extract free rent
        free_rent_pattern = r'(\d+)\s*months?\s*(?:of\s*)?(?:free|abated)\s*rent'
        free_match = re.search(free_rent_pattern, text, re.IGNORECASE)
        if free_match:
            data["free_rent_periods"].append({
                "duration_months": int(free_match.group(1)),
                "type": "free_rent"
            })
            
        confidence = 0.9 if data["base_rent_amount"] else 0.3
        
        if not data["base_rent_amount"]:
            warnings.append("No base rent amount found")
            
        return ExtractionResult(
            extracted_data=data,
            confidence=confidence,
            warnings=warnings
        )
        
    def extract_percentage_rent(self, text: str) -> ExtractionResult:
        """Extract percentage rent with breakpoints"""
        data = {
            "has_percentage_rent": False,
            "base_percentage": None,
            "breakpoints": [],
            "exclusions": [],
            "gross_sales_definition": None
        }
        warnings = []
        
        # Check if percentage rent exists
        if not re.search(r'percentage\s*rent', text, re.IGNORECASE):
            return ExtractionResult(
                extracted_data=data,
                confidence=0.9,
                warnings=["No percentage rent clause found"]
            )
            
        data["has_percentage_rent"] = True
        
        # Extract base percentage
        base_pattern = r'(\d+(?:\.\d+)?)\s*%\s*of\s*(?:gross\s*)?sales'
        base_match = re.search(base_pattern, text, re.IGNORECASE)
        if base_match:
            data["base_percentage"] = float(base_match.group(1))
            
        # Extract breakpoints
        breakpoint_pattern = r'(\d+(?:\.\d+)?)\s*%.*?excess.*?(' + self.currency_pattern + ')'
        for match in re.finditer(breakpoint_pattern, text, re.IGNORECASE):
            data["breakpoints"].append({
                "percentage": float(match.group(1)),
                "threshold": self._parse_currency(match.group(2))
            })
            
        # Extract exclusions
        exclusion_keywords = [
            'excluding', 'except', 'less', 'deducting', 'not including'
        ]
        for keyword in exclusion_keywords:
            pattern = rf'{keyword}\s+([^,\.]+(?:,\s*[^,\.]+)*)'
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                exclusions = [e.strip() for e in match.group(1).split(',')]
                data["exclusions"].extend(exclusions)
                
        confidence = 0.85 if data["base_percentage"] else 0.5
        
        return ExtractionResult(
            extracted_data=data,
            confidence=confidence,
            warnings=warnings
        )
        
    def extract_cam_charges(self, text: str) -> ExtractionResult:
        """Extract CAM charges and reconciliation terms"""
        data = {
            "cam_structure": None,  # pro_rata, fixed, cap_and_floor
            "estimated_cam": None,
            "cam_includes": [],
            "cam_excludes": [],
            "reconciliation_frequency": None,
            "cap_percentage": None,
            "admin_fee": None
        }
        warnings = []
        
        # Determine CAM structure
        if re.search(r'pro[\s-]*rata\s*share', text, re.IGNORECASE):
            data["cam_structure"] = "pro_rata"
        elif re.search(r'fixed\s*(?:cam|common\s*area)', text, re.IGNORECASE):
            data["cam_structure"] = "fixed"
            
        # Extract estimated CAM
        cam_pattern = r'estimated.*?(?:cam|common\s*area).*?(' + self.currency_pattern + ')'
        cam_match = re.search(cam_pattern, text, re.IGNORECASE)
        if cam_match:
            data["estimated_cam"] = self._parse_currency(cam_match.group(1))
            
        # Extract cap
        cap_pattern = r'cap.*?(\d+(?:\.\d+)?)\s*%'
        cap_match = re.search(cap_pattern, text, re.IGNORECASE)
        if cap_match:
            data["cap_percentage"] = float(cap_match.group(1))
            
        # Extract admin fee
        admin_pattern = r'admin\w*\s*fee.*?(\d+(?:\.\d+)?)\s*%'
        admin_match = re.search(admin_pattern, text, re.IGNORECASE)
        if admin_match:
            data["admin_fee"] = float(admin_match.group(1))
            
        # Extract reconciliation frequency
        if re.search(r'annual\w*\s*reconcil', text, re.IGNORECASE):
            data["reconciliation_frequency"] = "annual"
        elif re.search(r'quarter\w*\s*reconcil', text, re.IGNORECASE):
            data["reconciliation_frequency"] = "quarterly"
            
        confidence = 0.8 if data["cam_structure"] else 0.4
        
        return ExtractionResult(
            extracted_data=data,
            confidence=confidence,
            warnings=warnings
        )
        
    def _parse_currency(self, currency_str: str) -> float:
        """Parse currency string to float"""
        # Remove $ and commas
        cleaned = currency_str.replace('$', '').replace(',', '')
        try:
            return float(cleaned)
        except ValueError:
            return 0.0
            
    def calculate_total_rent(self, base_rent: float, percentage_rent: float, 
                           cam: float, other_charges: Dict[str, float]) -> ExtractionResult:
        """Calculate total rent obligations"""
        calculation = {
            "base_rent": base_rent,
            "percentage_rent": percentage_rent,
            "cam_charges": cam,
            "other_charges": other_charges,
            "subtotal": base_rent + percentage_rent + cam + sum(other_charges.values()),
            "estimated_annual": (base_rent + cam + sum(other_charges.values())) * 12
        }
        
        return ExtractionResult(
            extracted_data={
                "total_monthly": calculation["subtotal"],
                "total_annual": calculation["estimated_annual"]
            },
            confidence=0.95,
            calculation_details=calculation
        )


class DateTimeExtractor:
    """
    Specialized extractor for dates, deadlines, and time-based provisions
    """
    
    def __init__(self):
        self.date_patterns = [
            r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})',
            r'(\w+)\s+(\d{1,2}),?\s+(\d{4})',
            r'(\d{1,2})(?:st|nd|rd|th)?\s+(?:day\s+of\s+)?(\w+),?\s+(\d{4})'
        ]
        self.relative_patterns = [
            r'(\d+)\s*(days?|months?|years?)\s*(?:from|after|before|prior\s*to)',
            r'within\s*(\d+)\s*(days?|months?|years?)',
            r'(?:no|not)\s*(?:later|more)\s*than\s*(\d+)\s*(days?|months?|years?)'
        ]
        
    def extract_critical_dates(self, text: str) -> ExtractionResult:
        """Extract all critical dates and deadlines"""
        data = {
            "lease_commencement": None,
            "rent_commencement": None,
            "lease_expiration": None,
            "option_deadlines": [],
            "notice_deadlines": [],
            "other_critical_dates": []
        }
        warnings = []
        
        # Extract commencement date
        commence_pattern = r'(?:lease\s*)?commenc\w+\s*date.*?(' + '|'.join(self.date_patterns) + ')'
        commence_match = re.search(commence_pattern, text, re.IGNORECASE)
        if commence_match:
            data["lease_commencement"] = self._parse_date(commence_match.group(1))
            
        # Extract expiration date
        expire_pattern = r'(?:lease\s*)?expir\w+.*?(' + '|'.join(self.date_patterns) + ')'
        expire_match = re.search(expire_pattern, text, re.IGNORECASE)
        if expire_match:
            data["lease_expiration"] = self._parse_date(expire_match.group(1))
            
        # Extract option deadlines
        option_pattern = r'option.*?(?:exercis|notic).*?(\d+)\s*(days?|months?)'
        for match in re.finditer(option_pattern, text, re.IGNORECASE):
            data["option_deadlines"].append({
                "description": match.group(0)[:100],
                "notice_period": int(match.group(1)),
                "period_unit": match.group(2)
            })
            
        confidence = 0.9 if data["lease_commencement"] else 0.5
        
        return ExtractionResult(
            extracted_data=data,
            confidence=confidence,
            warnings=warnings
        )
        
    def extract_notice_periods(self, text: str) -> ExtractionResult:
        """Extract all notice periods and cure periods"""
        data = {
            "default_notice": None,
            "cure_period": None,
            "termination_notice": None,
            "renewal_notice": None,
            "other_notices": []
        }
        warnings = []
        
        # Extract default notice
        default_pattern = r'default.*?notice.*?(\d+)\s*(days?|months?)'
        default_match = re.search(default_pattern, text, re.IGNORECASE)
        if default_match:
            data["default_notice"] = {
                "period": int(default_match.group(1)),
                "unit": default_match.group(2)
            }
            
        # Extract cure period
        cure_pattern = r'cure.*?(\d+)\s*(days?|months?)'
        cure_match = re.search(cure_pattern, text, re.IGNORECASE)
        if cure_match:
            data["cure_period"] = {
                "period": int(cure_match.group(1)),
                "unit": cure_match.group(2)
            }
            
        confidence = 0.85
        
        return ExtractionResult(
            extracted_data=data,
            confidence=confidence,
            warnings=warnings
        )
        
    def calculate_deadline(self, base_date: datetime, period: int, 
                          unit: str, before: bool = False) -> datetime:
        """Calculate deadline based on base date and period"""
        if unit.startswith('day'):
            delta = timedelta(days=period)
        elif unit.startswith('month'):
            delta = timedelta(days=period * 30)  # Approximate
        elif unit.startswith('year'):
            delta = timedelta(days=period * 365)
        else:
            delta = timedelta(days=0)
            
        if before:
            return base_date - delta
        else:
            return base_date + delta
            
    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse various date formats"""
        # This is simplified - in production, use dateutil.parser
        try:
            # Try MM/DD/YYYY format
            if '/' in date_str or '-' in date_str:
                parts = re.split('[/-]', date_str)
                if len(parts) == 3:
                    month, day, year = parts
                    if len(year) == 2:
                        year = '20' + year
                    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            return date_str
        except:
            return None


class ConditionalClauseExtractor:
    """
    Specialized extractor for conditional clauses and triggering events
    """
    
    def __init__(self):
        self.condition_patterns = [
            r'(?:if|when|in\s*the\s*event)\s+([^,]+),?\s*(?:then|tenant|landlord)',
            r'(?:provided\s*that|on\s*condition\s*that|subject\s*to)\s+([^,]+)',
            r'(?:unless|except\s*if|but\s*only\s*if)\s+([^,]+)'
        ]
        
    def extract_conditional_rights(self, text: str) -> ExtractionResult:
        """Extract conditional rights and obligations"""
        data = {
            "conditional_rights": [],
            "triggering_events": [],
            "conditions_precedent": [],
            "conditions_subsequent": []
        }
        warnings = []
        
        # Extract if-then conditions
        if_then_pattern = r'if\s+([^,]+),?\s*then\s+([^\.]+)'
        for match in re.finditer(if_then_pattern, text, re.IGNORECASE):
            data["conditional_rights"].append({
                "condition": match.group(1).strip(),
                "consequence": match.group(2).strip(),
                "type": "if_then"
            })
            
        # Extract triggering events
        trigger_keywords = [
            'sale', 'assignment', 'default', 'bankruptcy', 'demolition',
            'condemnation', 'casualty', 'change of control'
        ]
        
        for keyword in trigger_keywords:
            if keyword in text.lower():
                # Find the context around the keyword
                pattern = rf'({keyword}[^\.]*\.)'
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    data["triggering_events"].append({
                        "event_type": keyword,
                        "description": match.group(1)
                    })
                    
        confidence = 0.8 if data["conditional_rights"] or data["triggering_events"] else 0.6
        
        return ExtractionResult(
            extracted_data=data,
            confidence=confidence,
            warnings=warnings
        )
        
    def extract_co_tenancy_provisions(self, text: str) -> ExtractionResult:
        """Extract co-tenancy requirements and remedies"""
        data = {
            "has_co_tenancy": False,
            "opening_co_tenancy": None,
            "ongoing_co_tenancy": None,
            "remedies": [],
            "cure_period": None
        }
        warnings = []
        
        if not re.search(r'co[\s-]*tenancy', text, re.IGNORECASE):
            return ExtractionResult(
                extracted_data=data,
                confidence=0.9,
                warnings=["No co-tenancy provisions found"]
            )
            
        data["has_co_tenancy"] = True
        
        # Extract opening co-tenancy
        opening_pattern = r'opening\s*co[\s-]*tenancy.*?(?:require|condition)([^\.]+)'
        opening_match = re.search(opening_pattern, text, re.IGNORECASE)
        if opening_match:
            data["opening_co_tenancy"] = opening_match.group(1).strip()
            
        # Extract remedies
        remedy_patterns = [
            r'(?:alternative|substitute|reduced)\s*rent.*?(\d+(?:\.\d+)?)\s*%',
            r'(?:terminate|termination).*?(?:right|option)',
            r'(?:abate|abatement).*?rent'
        ]
        
        for pattern in remedy_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data["remedies"].append(match.group(0)[:200])
                
        confidence = 0.85 if data["opening_co_tenancy"] or data["remedies"] else 0.6
        
        return ExtractionResult(
            extracted_data=data,
            confidence=confidence,
            warnings=warnings
        )


class RightsAndOptionsExtractor:
    """
    Specialized extractor for rights, options, and special provisions
    """
    
    def __init__(self):
        self.option_types = [
            'renewal', 'extension', 'expansion', 'contraction', 
            'termination', 'purchase', 'first refusal', 'first offer'
        ]
        
    def extract_renewal_options(self, text: str) -> ExtractionResult:
        """Extract renewal and extension options"""
        data = {
            "renewal_options": [],
            "total_potential_term": None,
            "renewal_rent_terms": None
        }
        warnings = []
        
        # Extract number of renewal options
        renewal_pattern = r'(\d+)\s*(?:renewal|extension)\s*option'
        match = re.search(renewal_pattern, text, re.IGNORECASE)
        if match:
            num_options = int(match.group(1))
            
            # Extract term for each option
            term_pattern = r'(\d+)[\s-]*year\s*(?:term|period)'
            term_match = re.search(term_pattern, text, re.IGNORECASE)
            if term_match:
                option_term = int(term_match.group(1))
                
                for i in range(num_options):
                    data["renewal_options"].append({
                        "option_number": i + 1,
                        "term_years": option_term,
                        "rent_determination": None
                    })
                    
        # Extract rent determination method
        if re.search(r'market\s*(?:rate|rent)', text, re.IGNORECASE):
            data["renewal_rent_terms"] = "market_rate"
        elif re.search(r'fixed\s*increase', text, re.IGNORECASE):
            data["renewal_rent_terms"] = "fixed_increase"
        elif re.search(r'same\s*(?:rate|rent)', text, re.IGNORECASE):
            data["renewal_rent_terms"] = "same_as_current"
            
        confidence = 0.9 if data["renewal_options"] else 0.5
        
        return ExtractionResult(
            extracted_data=data,
            confidence=confidence,
            warnings=warnings
        )
        
    def extract_expansion_rights(self, text: str) -> ExtractionResult:
        """Extract expansion and ROFR/ROFO rights"""
        data = {
            "expansion_rights": [],
            "rofr": False,
            "rofo": False,
            "must_take_space": []
        }
        warnings = []
        
        # Check for ROFR
        if re.search(r'right\s*of\s*first\s*refusal', text, re.IGNORECASE):
            data["rofr"] = True
            
        # Check for ROFO
        if re.search(r'right\s*of\s*first\s*offer', text, re.IGNORECASE):
            data["rofo"] = True
            
        # Extract expansion rights
        expansion_pattern = r'(?:right|option)\s*to\s*(?:lease|expand).*?(?:additional|adjacent|contiguous)\s*(?:space|premises)'
        if re.search(expansion_pattern, text, re.IGNORECASE):
            data["expansion_rights"].append({
                "type": "expansion_option",
                "description": "Tenant has expansion rights"
            })
            
        confidence = 0.85 if any([data["rofr"], data["rofo"], data["expansion_rights"]]) else 0.6
        
        return ExtractionResult(
            extracted_data=data,
            confidence=confidence,
            warnings=warnings
        )


def create_specialized_extractor(clause_type: str):
    """Factory function to create appropriate specialized extractor"""
    extractors = {
        "financial": FinancialClauseExtractor(),
        "datetime": DateTimeExtractor(),
        "conditional": ConditionalClauseExtractor(),
        "rights": RightsAndOptionsExtractor()
    }
    
    return extractors.get(clause_type)
