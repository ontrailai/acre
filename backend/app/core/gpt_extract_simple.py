"""
Improved GPT extraction module with better error handling and debugging
"""

from typing import List, Dict, Any, Tuple, Optional
import json
import os
import asyncio
import time
import openai
import re
from app.schemas import LeaseType, ClauseExtraction
from app.utils.logger import logger
from app.core.improved_prompts import get_optimized_lease_prompts, get_fallback_extraction_prompt
from app.core.residential_patterns import extract_residential_lease_patterns, merge_extraction_results
from app.core.pattern_converter import _convert_extracted_data_to_clauses

# Import the original functions we need
from app.core.gpt_extract import (
    CLAUSE_INDICATORS, RISK_PATTERNS, is_template_lease, 
    detect_risk_tags, infer_clause_type, deduplicate_clauses,
    _has_hierarchical_structure
)


async def extract_clauses_simple(segments: List[Dict[str, Any]], lease_type: LeaseType) -> Dict[str, ClauseExtraction]:
    """
    Simplified extraction that focuses on getting basic lease information
    """
    logger.info(f"Starting simplified extraction for {len(segments)} segments")
    
    all_clauses = {}
    
    # First, try pattern matching on all segments
    pattern_results = _extract_with_patterns(segments)
    if pattern_results:
        all_clauses.update(pattern_results)
        logger.info(f"Pattern matching found {len(pattern_results)} clauses")
    
    # Combine all text for GPT extraction
    full_text = "\n\n".join(seg.get("content", "") for seg in segments if seg.get("content"))
    
    if len(full_text.strip()) < 100:
        logger.error("Document text too short for extraction")
        return all_clauses if all_clauses else _create_minimal_extraction("")
    
    # Try multiple GPT extraction strategies
    gpt_results = await _extract_with_gpt_multiple_strategies(full_text, segments)
    
    # Merge results, preferring GPT over patterns
    for key, clause in gpt_results.items():
        if key in all_clauses:
            # Merge data if both have values
            existing_data = all_clauses[key].structured_data or {}
            new_data = clause.structured_data or {}
            
            # Combine, preferring non-null values
            merged_data = {}
            for k in set(existing_data.keys()) | set(new_data.keys()):
                if new_data.get(k) is not None:
                    merged_data[k] = new_data[k]
                elif existing_data.get(k) is not None:
                    merged_data[k] = existing_data[k]
            
            clause.structured_data = merged_data
            clause.content = json.dumps(merged_data, indent=2)
        
        all_clauses[key] = clause
    
    # If still minimal results, create a comprehensive fallback
    if len(all_clauses) < 3:
        logger.warning(f"Only found {len(all_clauses)} clauses, adding comprehensive fallback")
        fallback_clauses = _create_comprehensive_fallback(full_text, segments)
        all_clauses.update(fallback_clauses)
    
    return all_clauses


def _extract_with_patterns(segments: List[Dict[str, Any]]) -> Dict[str, ClauseExtraction]:
    """Extract using improved pattern matching"""
    all_clauses = {}
    
    # Combine all segments for better context
    full_text = "\n\n".join(seg.get("content", "") for seg in segments)
    
    # First try residential lease patterns
    residential_data = extract_residential_lease_patterns(full_text)
    if residential_data:
        logger.info(f"Residential patterns extracted: {list(residential_data.keys())}")
        # Convert to clauses
        residential_clauses = _convert_extracted_data_to_clauses(residential_data)
        all_clauses.update(residential_clauses)
    
    # Enhanced patterns with more variations
    extraction_patterns = {
        "parties": {
            "landlord": [
                r"(?:Landlord|LANDLORD|Lessor|LESSOR)[:\s]*([A-Za-z0-9\s\.,&'-]+?)(?:\n|,|\(|hereinafter)",
                r"between\s+([A-Za-z0-9\s\.,&'-]+?)(?:\s*\(.*?[Ll]andlord.*?\)|.*?,\s*a[s]?\s+[Ll]andlord)",
                r'"([A-Za-z0-9\s\.,&\'-]+?)"\s*(?:hereinafter.*?)?[Ll]andlord',
                r'\("([A-Za-z0-9\s\.,&\'-]+?)"\),?\s*(?:a[s]?\s+)?[Ll]andlord'
            ],
            "tenant": [
                r"(?:Tenant|TENANT|Lessee|LESSEE)[:\s]*([A-Za-z0-9\s\.,&'-]+?)(?:\n|,|\(|hereinafter)",
                r"and\s+([A-Za-z0-9\s\.,&'-]+?)(?:\s*\(.*?[Tt]enant.*?\)|.*?,\s*a[s]?\s+[Tt]enant)",
                r'"([A-Za-z0-9\s\.,&\'-]+?)"\s*(?:hereinafter.*?)?[Tt]enant',
                r'\("([A-Za-z0-9\s\.,&\'-]+?)"\),?\s*(?:a[s]?\s+)?[Tt]enant'
            ]
        },
        "premises": {
            "address": [
                r"(?:Premises|Property|Located at|Address)[:\s]*([0-9]+[^,\n]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Way|Boulevard|Blvd|Parkway|Pkwy|Court|Ct|Place|Pl)[^,\n]*)",
                r"premises.*?located at[:\s]*([^,\n]+)",
                r"property.*?known as[:\s]*([^,\n]+)",
                r"(\d+\s+[A-Za-z0-9\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Way|Boulevard|Blvd)[^,\n]*)"
            ],
            "square_feet": [
                r"([\d,]+)\s*(?:square feet|sq\.?\s*ft\.?|SF|sf|Square Feet)",
                r"approximately\s*([\d,]+)\s*(?:rentable|usable|leasable)?\s*(?:square feet|sq\.?\s*ft\.?)",
                r"(?:containing|consisting of|comprising)\s*([\d,]+)\s*(?:square feet|sq\.?\s*ft\.?)"
            ],
            "suite": [
                r"(?:Suite|Unit|Space|#)\s*([A-Za-z0-9-]+)",
                r"(?:suite|unit)\s+(?:number|no\.?|#)?\s*([A-Za-z0-9-]+)"
            ]
        },
        "term": {
            "commencement_date": [
                r"(?:Commencement Date|Term Commencement|Lease Commencement|Beginning)[:\s]*([A-Za-z]+\s+\d{1,2},?\s+\d{2,4})",
                r"(?:commencing|beginning|starting)\s+(?:on|as of)?[:\s]*([A-Za-z]+\s+\d{1,2},?\s+\d{2,4})",
                r"(?:effective|Effective Date)[:\s]*([A-Za-z]+\s+\d{1,2},?\s+\d{2,4})",
                r"term.*?shall.*?commence.*?on[:\s]*([A-Za-z]+\s+\d{1,2},?\s+\d{2,4})"
            ],
            "expiration_date": [
                r"(?:Expiration Date|Termination Date|Ending)[:\s]*([A-Za-z]+\s+\d{1,2},?\s+\d{2,4})",
                r"(?:expiring|ending|terminating)\s+(?:on)?[:\s]*([A-Za-z]+\s+\d{1,2},?\s+\d{2,4})",
                r"through[:\s]*([A-Za-z]+\s+\d{1,2},?\s+\d{2,4})"
            ],
            "term_length": [
                r"(?:Term|Initial Term|Lease Term)[:\s]*(\d+)\s*(?:years?|months?)",
                r"for\s+(?:a period of\s+)?(\d+)\s*(?:years?|months?)",
                r"(\d+)[\s-]*(?:year|month)\s+(?:term|period|lease)"
            ]
        },
        "rent": {
            "base_rent": [
                r"\$\s*([\d,]+(?:\.\d{2})?)\s*(?:per month|/month|monthly)",
                r"(?:Base Rent|Monthly Rent|Rent)[:\s]*\$\s*([\d,]+(?:\.\d{2})?)",
                r"monthly.*?rent.*?\$\s*([\d,]+(?:\.\d{2})?)",
                r"rent.*?amount.*?\$\s*([\d,]+(?:\.\d{2})?)"
            ],
            "annual_rent": [
                r"\$\s*([\d,]+(?:\.\d{2})?)\s*(?:per year|/year|annually|per annum)",
                r"(?:Annual Rent|Yearly Rent)[:\s]*\$\s*([\d,]+(?:\.\d{2})?)"
            ]
        }
    }
    
    # Extract using patterns
    for category, patterns_dict in extraction_patterns.items():
        extracted_data = {}
        
        for field, patterns in patterns_dict.items():
            for pattern in patterns:
                match = re.search(pattern, full_text, re.IGNORECASE | re.MULTILINE)
                if match:
                    value = match.group(1).strip()
                    # Clean up the value
                    value = re.sub(r'\s+', ' ', value)  # Normalize whitespace
                    value = value.strip(' ,.')  # Remove trailing punctuation
                    
                    if value and len(value) > 2:  # Ensure meaningful value
                        extracted_data[field] = value
                        logger.debug(f"Pattern matched {field}: {value}")
                        break
        
        # Create clause if we found data
        if extracted_data:
            clause_key = f"{category}_data"
            all_clauses[clause_key] = ClauseExtraction(
                content=json.dumps(extracted_data, indent=2),
                raw_excerpt=f"Extracted {category} information from document",
                confidence=0.7,
                page_number=1,
                risk_tags=[],
                summary_bullet=f"{category.title()} information",
                structured_data=extracted_data,
                needs_review=False,
                field_id=category
            )
    
    return all_clauses


async def _extract_with_gpt_multiple_strategies(full_text: str, segments: List[Dict[str, Any]]) -> Dict[str, ClauseExtraction]:
    """Try multiple GPT strategies to extract information"""
    all_clauses = {}
    
    # Strategy 1: Focused extraction on first 8000 chars
    focused_text = full_text[:8000]
    
    system_prompt = """You are a lease extraction expert. Extract specific values from the lease text.
Focus on finding actual names, addresses, dates, and amounts - not descriptions.
If you see partial information, include it."""
    
    user_prompt = f"""Extract these specific items from this lease:

{focused_text}

Extract:
- Landlord name (company or person name)
- Tenant name (company or person name)  
- Property address (full street address)
- Suite/Unit number
- Square footage (number only)
- Commencement date (actual date)
- Expiration date (actual date)
- Term length (in months or years)
- Monthly rent amount (dollar amount)
- Security deposit amount
- Permitted use

Return JSON with exact field names. Use null for missing values."""

    try:
        response = await call_openai_api_simple(system_prompt, user_prompt)
        
        if response:
            logger.info(f"GPT response received: {response[:200]}...")
            data = _parse_gpt_response(response)
            
            if data and any(v is not None and v != "" for v in data.values()):
                logger.info(f"Successfully parsed JSON with keys: {list(data.keys())}")
                clauses = _convert_gpt_data_to_clauses(data)
                all_clauses.update(clauses)
    except Exception as e:
        logger.error(f"Strategy 1 GPT extraction error: {e}")
    
    # Strategy 2: If we're missing key data, try section-by-section
    missing_keys = ["landlord", "tenant", "address", "monthly_rent"]
    found_keys = set()
    for clause in all_clauses.values():
        if clause.structured_data:
            found_keys.update(clause.structured_data.keys())
    
    still_missing = [k for k in missing_keys if k not in found_keys and f"{k}_name" not in found_keys]
    
    if still_missing:
        logger.info(f"Still missing: {still_missing}, trying section-by-section extraction")
        
        # Extract from key sections
        for segment in segments[:5]:  # First 5 segments usually have key info
            if not segment.get("content"):
                continue
                
            section_prompt = f"""Find these values in this section:
{segment['content'][:2000]}

Looking for: {', '.join(still_missing)}
Return as JSON."""
            
            try:
                response = await call_openai_api_simple("Extract lease values. Return JSON.", section_prompt)
                if response:
                    data = _parse_gpt_response(response)
                    if data:
                        section_clauses = _convert_gpt_data_to_clauses(data)
                        all_clauses.update(section_clauses)
            except:
                continue
    
    return all_clauses


def _parse_gpt_response(response: str) -> Dict[str, Any]:
    """Parse GPT response more robustly"""
    try:
        # First try direct JSON parsing
        return json.loads(response)
    except:
        pass
    
    try:
        # Try to extract JSON from response
        json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
    except:
        pass
    
    # If JSON parsing fails, try to extract key-value pairs
    data = {}
    
    # Extended patterns for common lease fields
    field_patterns = [
        (r"landlord[:\s]*([^\n]+)", "landlord"),
        (r"tenant[:\s]*([^\n]+)", "tenant"),
        (r"address[:\s]*([^\n]+)", "address"),
        (r"suite[:\s]*([^\n]+)", "suite"),
        (r"square\s*feet[:\s]*([^\n]+)", "square_feet"),
        (r"commencement[:\s]*([^\n]+)", "commencement_date"),
        (r"expiration[:\s]*([^\n]+)", "expiration_date"),
        (r"term[:\s]*([^\n]+)", "term_length"),
        (r"monthly\s*rent[:\s]*([^\n]+)", "monthly_rent"),
        (r"rent[:\s]*([^\n]+)", "monthly_rent"),
        (r"security\s*deposit[:\s]*([^\n]+)", "security_deposit"),
        (r"permitted\s*use[:\s]*([^\n]+)", "permitted_use"),
    ]
    
    for pattern, key in field_patterns:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            value = match.group(1).strip().strip('"').strip("'")
            if value and value.lower() not in ["null", "none", "n/a", ""]:
                data[key] = value
    
    return data if data else None


def _convert_gpt_data_to_clauses(data: Dict[str, Any]) -> Dict[str, ClauseExtraction]:
    """Convert GPT extracted data to proper clause format with better organization"""
    clauses = {}
    
    # Group related fields
    if any(data.get(k) for k in ["landlord", "tenant"]):
        clauses["parties_data"] = ClauseExtraction(
            content=json.dumps({
                "landlord_name": data.get("landlord"),
                "tenant_name": data.get("tenant")
            }, indent=2),
            raw_excerpt="Extracted party information",
            confidence=0.8,
            page_number=1,
            risk_tags=[],
            summary_bullet=f"Landlord: {data.get('landlord', 'Not found')} | Tenant: {data.get('tenant', 'Not found')}",
            structured_data={
                "landlord_name": data.get("landlord"),
                "tenant_name": data.get("tenant")
            },
            needs_review=False,
            field_id="parties"
        )
    
    if any(data.get(k) for k in ["address", "square_feet", "suite"]):
        address_full = data.get("address", "")
        if data.get("suite"):
            address_full = f"{address_full}, Suite {data.get('suite')}" if address_full else f"Suite {data.get('suite')}"
            
        clauses["premises_data"] = ClauseExtraction(
            content=json.dumps({
                "address": address_full,
                "square_feet": data.get("square_feet"),
                "suite": data.get("suite")
            }, indent=2),
            raw_excerpt="Extracted premises information",
            confidence=0.8,
            page_number=1,
            risk_tags=[],
            summary_bullet=f"Property: {address_full} ({data.get('square_feet', 'Unknown')} sq ft)",
            structured_data={
                "address": address_full,
                "square_feet": data.get("square_feet"),
                "suite": data.get("suite")
            },
            needs_review=False,
            field_id="premises"
        )
    
    if any(data.get(k) for k in ["commencement_date", "expiration_date", "term_length", "term_months"]):
        clauses["term_data"] = ClauseExtraction(
            content=json.dumps({
                "commencement_date": data.get("commencement_date"),
                "expiration_date": data.get("expiration_date"),
                "term_length": data.get("term_length") or data.get("term_months")
            }, indent=2),
            raw_excerpt="Extracted term information",
            confidence=0.8,
            page_number=1,
            risk_tags=[],
            summary_bullet=f"Term: {data.get('commencement_date', 'TBD')} to {data.get('expiration_date', 'TBD')} ({data.get('term_length', 'Unknown duration')})",
            structured_data={
                "commencement_date": data.get("commencement_date"),
                "expiration_date": data.get("expiration_date"),
                "term_length": data.get("term_length") or data.get("term_months")
            },
            needs_review=False,
            field_id="term"
        )
    
    if data.get("monthly_rent") or data.get("annual_rent"):
        monthly = data.get("monthly_rent")
        annual = data.get("annual_rent")
        
        # Convert annual to monthly if needed
        if annual and not monthly:
            try:
                annual_num = float(re.sub(r'[^\d.]', '', annual))
                monthly = f"${annual_num/12:,.2f}"
            except:
                pass
                
        clauses["rent_data"] = ClauseExtraction(
            content=json.dumps({
                "base_rent": monthly,
                "annual_rent": annual
            }, indent=2),
            raw_excerpt="Extracted rent information",
            confidence=0.8,
            page_number=1,
            risk_tags=[],
            summary_bullet=f"Base Rent: {monthly or 'Not specified'}/month",
            structured_data={
                "base_rent": monthly,
                "annual_rent": annual
            },
            needs_review=False,
            field_id="rent"
        )
    
    if data.get("permitted_use"):
        clauses["use_data"] = ClauseExtraction(
            content=json.dumps({"permitted_use": data.get("permitted_use")}, indent=2),
            raw_excerpt="Extracted use information",
            confidence=0.8,
            page_number=1,
            risk_tags=[],
            summary_bullet=f"Permitted Use: {data.get('permitted_use')}",
            structured_data={"permitted_use": data.get("permitted_use")},
            needs_review=False,
            field_id="use"
        )
    
    if data.get("security_deposit"):
        clauses["security_deposit_data"] = ClauseExtraction(
            content=json.dumps({"amount": data.get("security_deposit")}, indent=2),
            raw_excerpt="Extracted security deposit information",
            confidence=0.8,
            page_number=1,
            risk_tags=[],
            summary_bullet=f"Security Deposit: {data.get('security_deposit')}",
            structured_data={"amount": data.get("security_deposit")},
            needs_review=False,
            field_id="security_deposit"
        )
    
    return clauses


def _create_comprehensive_fallback(text: str, segments: List[Dict[str, Any]]) -> Dict[str, ClauseExtraction]:
    """Create a comprehensive fallback with document overview"""
    
    # Try to identify document type
    doc_indicators = {
        "lease": ["lease agreement", "landlord and tenant", "rent", "premises", "term of lease"],
        "amendment": ["amendment", "modifies", "amends", "changes to"],
        "sublease": ["sublease", "sublandlord", "subtenant"],
        "assignment": ["assignment", "assignor", "assignee"],
    }
    
    doc_type = "lease"
    for dtype, indicators in doc_indicators.items():
        if any(ind in text.lower() for ind in indicators):
            doc_type = dtype
            break
    
    # Count pages
    page_count = max((seg.get("page_end", 1) for seg in segments), default=1)
    
    # Look for any dates in the document
    date_pattern = r"([A-Za-z]+\s+\d{1,2},?\s+\d{2,4})"
    dates_found = re.findall(date_pattern, text)
    
    # Look for any dollar amounts
    money_pattern = r"\$\s*([\d,]+(?:\.\d{2})?)"
    amounts_found = re.findall(money_pattern, text)
    
    return {
        "document_overview_data": ClauseExtraction(
            content=json.dumps({
                "document_type": doc_type,
                "page_count": page_count,
                "extraction_status": "partial",
                "dates_found": dates_found[:3] if dates_found else [],
                "amounts_found": amounts_found[:3] if amounts_found else [],
                "word_count": len(text.split()),
                "note": "Automated extraction found limited structured data. Key terms detected in document."
            }, indent=2),
            raw_excerpt=text[:500] + "...",
            confidence=0.4,
            page_number=1,
            risk_tags=[{
                "type": "incomplete_extraction",
                "level": "medium",
                "description": "Automated extraction was partially successful. Manual review recommended for complete information."
            }],
            summary_bullet=f"Document appears to be a {doc_type} ({page_count} pages, {len(text.split())} words)",
            structured_data={
                "document_type": doc_type,
                "page_count": page_count,
                "dates_found": dates_found[:3] if dates_found else [],
                "amounts_found": amounts_found[:3] if amounts_found else []
            },
            needs_review=True,
            field_id="document_overview"
        )
    }


def _create_minimal_extraction(text: str) -> Dict[str, ClauseExtraction]:
    """Create minimal extraction as last resort"""
    return {
        "error_data": ClauseExtraction(
            content=json.dumps({
                "extraction_status": "failed",
                "error": "Unable to extract lease information",
                "suggestion": "Please ensure this is a valid lease document"
            }, indent=2),
            raw_excerpt=text[:300] + "..." if text else "No content",
            confidence=0.1,
            page_number=1,
            risk_tags=[{
                "type": "extraction_failed",
                "level": "high",
                "description": "Automated extraction failed completely - manual review required"
            }],
            summary_bullet="Extraction failed - manual review required",
            structured_data={"extraction_status": "failed"},
            needs_review=True,
            field_id="error"
        )
    }


async def call_openai_api_simple(system_prompt: str, user_prompt: str) -> Optional[str]:
    """Simplified OpenAI API call with better error handling"""
    try:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logger.error("OpenAI API key not found")
            return None
            
        # Log token estimation
        total_prompt = system_prompt + user_prompt
        estimated_tokens = len(total_prompt.split()) * 1.3  # Rough estimation
        logger.info(f"Estimated prompt tokens: {estimated_tokens}")
        
        if estimated_tokens > 3000:
            logger.warning(f"Prompt may be too long ({estimated_tokens} estimated tokens)")
            # Truncate user prompt if too long
            max_chars = int(3000 * 4)  # Roughly 4 chars per token
            if len(user_prompt) > max_chars:
                user_prompt = user_prompt[:max_chars] + "\n\n[Content truncated...]"
        
        # Use synchronous client
        client = openai.OpenAI(api_key=api_key)
        
        logger.info("Making GPT-4 API call...")
        response = client.chat.completions.create(
            model="gpt-4",  # Use regular GPT-4, not turbo
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=1000,  # Limit response size
            # Don't force JSON mode - let GPT respond naturally
        )
        
        content = response.choices[0].message.content
        logger.info(f"GPT-4 responded with {len(content)} characters")
        
        return content
        
    except Exception as e:
        logger.error(f"OpenAI API error: {type(e).__name__}: {str(e)}")
        return None


# Override the main extraction function
async def extract_clauses(segments: List[Dict[str, Any]], lease_type: LeaseType, use_ast: bool = True) -> Dict[str, ClauseExtraction]:
    """
    Use simplified extraction approach
    """
    return await extract_clauses_simple(segments, lease_type)
