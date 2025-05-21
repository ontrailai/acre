from typing import Dict, List, Any, Tuple, Optional, Set
from app.schemas import LeaseType, ClauseExtraction, RiskLevel, RiskFlag
from app.utils.logger import logger
from app.utils.risk_analysis.enums import ClauseCategory
from app.utils.risk_analysis.clause_catalog import get_essential_clauses
import re
import json
import os
from datetime import datetime

# Constants
MIN_CLAUSE_CONFIDENCE_THRESHOLD = 0.4
ANALYSIS_LOG_DIR = os.path.join("app", "storage", "logs", "risk_analysis")

# Create log directory
os.makedirs(ANALYSIS_LOG_DIR, exist_ok=True)

def analyze_risks(clauses: Dict[str, ClauseExtraction], lease_type: LeaseType) -> Tuple[List[RiskFlag], List[Dict]]:
    """
    Analyze lease clauses for potential risks.
    
    Args:
        clauses: Dictionary of extracted lease clauses
        lease_type: Type of the lease (RETAIL, OFFICE, INDUSTRIAL)
        
    Returns:
        - A list of risk flags with details
        - A list of missing clauses metadata
    """
    try:
        # Initialize results
        risk_flags = []
        clause_analysis_logs = []
        
        # Check for missing essential clauses
        missing_clauses = check_missing_essential_clauses(clauses, lease_type)
        
        # Log missing clauses for debugging
        log_missing_clauses(missing_clauses, lease_type)
        
        # Analyze existing clauses for risks
        for key, clause in clauses.items():
            # Skip low confidence clauses
            if hasattr(clause, 'confidence') and clause.confidence < MIN_CLAUSE_CONFIDENCE_THRESHOLD:
                clause_analysis_logs.append({
                    "clause_key": key,
                    "confidence": getattr(clause, 'confidence', None),
                    "matched_heuristics": [],
                    "skipped": True,
                    "reason": f"Low confidence: {getattr(clause, 'confidence', 'unknown')}"
                })
                logger.info(f"Skipping risk analysis for low-confidence clause: {key}")
                continue
            
            # First, check for risks already identified in GPT extraction
            if clause.risk_tags:
                for risk in clause.risk_tags:
                    risk_flags.append(RiskFlag(
                        clause_key=key,
                        clause_name=key.replace("_", " ").title(),
                        level=risk.get("level", RiskLevel.MEDIUM),
                        description=risk.get("description", "Unspecified risk"),
                        source="gpt_extraction",
                        related_text=clause.raw_excerpt[:100] + "..." if len(clause.raw_excerpt) > 100 else clause.raw_excerpt,
                        page_number=clause.page_number
                    ))
                    
                    # Add to analysis log
                    if not any(log["clause_key"] == key for log in clause_analysis_logs):
                        clause_analysis_logs.append({
                            "clause_key": key,
                            "confidence": getattr(clause, 'confidence', None),
                            "matched_heuristics": ["gpt_risk_tags"],
                            "skipped": False
                        })
            
            # Then, perform additional risk analysis based on specialized checks
            additional_risks, matched_heuristics = analyze_clause_risks(key, clause, lease_type)
            risk_flags.extend(additional_risks)
            
            # Update analysis log
            current_log = next((log for log in clause_analysis_logs if log["clause_key"] == key), None)
            if current_log:
                current_log["matched_heuristics"].extend(matched_heuristics)
            else:
                clause_analysis_logs.append({
                    "clause_key": key,
                    "confidence": getattr(clause, 'confidence', None),
                    "matched_heuristics": matched_heuristics,
                    "skipped": False
                })
        
        # Add lease-type specific risk analysis
        if lease_type == LeaseType.RETAIL:
            retail_risks, retail_heuristics = analyze_retail_specific_risks(clauses)
            risk_flags.extend(retail_risks)
            # Update logs with retail heuristics
            update_analysis_logs(clause_analysis_logs, retail_heuristics)
            
        elif lease_type == LeaseType.OFFICE:
            office_risks, office_heuristics = analyze_office_specific_risks(clauses)
            risk_flags.extend(office_risks)
            # Update logs with office heuristics
            update_analysis_logs(clause_analysis_logs, office_heuristics)
            
        elif lease_type == LeaseType.INDUSTRIAL:
            industrial_risks, industrial_heuristics = analyze_industrial_specific_risks(clauses)
            risk_flags.extend(industrial_risks)
            # Update logs with industrial heuristics
            update_analysis_logs(clause_analysis_logs, industrial_heuristics)
        
        # Check for cross-clause risks (issues that span multiple clauses)
        cross_clause_risks, cross_heuristics = analyze_cross_clause_risks(clauses, lease_type)
        risk_flags.extend(cross_clause_risks)
        # Update logs with cross-clause heuristics
        update_analysis_logs(clause_analysis_logs, cross_heuristics)
        
        # De-duplicate risk flags
        risk_flags = deduplicate_risks(risk_flags)
        
        # Save analysis logs
        save_analysis_logs(clause_analysis_logs, lease_type)
        
        logger.info(f"Risk analysis complete. Found {len(risk_flags)} risks and {len(missing_clauses)} missing clauses")
        return risk_flags, missing_clauses
        
    except Exception as e:
        logger.error(f"Error analyzing risks: {str(e)}")
        return [], []


def update_analysis_logs(analysis_logs: List[Dict], heuristics_by_clause: Dict[str, List[str]]):
    """Update analysis logs with new heuristics"""
    for clause_key, heuristics in heuristics_by_clause.items():
        current_log = next((log for log in analysis_logs if log["clause_key"] == clause_key), None)
        if current_log:
            current_log["matched_heuristics"].extend(heuristics)
        else:
            analysis_logs.append({
                "clause_key": clause_key,
                "confidence": None,  # Unknown confidence for cross-clause analysis
                "matched_heuristics": heuristics,
                "skipped": False
            })


def save_analysis_logs(analysis_logs: List[Dict], lease_type: LeaseType):
    """Save analysis logs to file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(ANALYSIS_LOG_DIR, f"clause_analysis_{lease_type.value}_{timestamp}.json")
    
    with open(log_path, "w") as f:
        json.dump(analysis_logs, f, indent=2)
    
    logger.info(f"Saved clause analysis logs to {log_path}")


def check_missing_essential_clauses(clauses: Dict[str, ClauseExtraction], lease_type: LeaseType) -> List[Dict]:
    """
    Check for missing essential clauses based on lease type.
    
    Args:
        clauses: Dictionary of extracted lease clauses
        lease_type: Type of lease
        
    Returns:
        List of dictionaries with missing clause metadata
    """
    # Get essential clauses for this lease type
    essential_clauses = get_essential_clauses(lease_type)
    
    # Check for missing clauses
    missing = []
    
    for category, keywords in essential_clauses.items():
        found = False
        
        # Check clause keys
        for key in clauses.keys():
            if any(keyword in key.lower() for keyword in keywords):
                found = True
                break
                
        # Also check in clause content
        if not found:
            for clause in clauses.values():
                if any(keyword in clause.content.lower() for keyword in keywords):
                    found = True
                    break
                
        # Check in structured data if available
        if not found:
            for clause in clauses.values():
                if clause.structured_data:
                    if any(keyword in str(clause.structured_data).lower() for keyword in keywords):
                        found = True
                        break
                    
        if not found:
            missing.append({
                "category": category.replace("_", " ").title(),
                "required_keywords": keywords,
                "match_found": False
            })
    
    return missing


def log_missing_clauses(missing_clauses: List[Dict], lease_type: LeaseType):
    """Log missing clauses to file for debugging"""
    if not missing_clauses:
        return
        
    # Create debug directory
    debug_dir = os.path.join("app", "storage", "debug")
    os.makedirs(debug_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    debug_path = os.path.join(debug_dir, f"missing_clause_debug_{lease_type.value}_{timestamp}.json")
    
    with open(debug_path, "w", encoding="utf-8") as f:
        json.dump(missing_clauses, f, indent=2)
        
    logger.info(f"Logged missing clause debug data to {debug_path}")


def analyze_clause_risks(key: str, clause: ClauseExtraction, lease_type: LeaseType) -> Tuple[List[RiskFlag], List[str]]:
    """
    Analyze a single clause for potential risks.
    
    Args:
        key: Clause key
        clause: Extracted clause data
        lease_type: Type of lease
        
    Returns:
        Tuple of:
        - List of risk flags identified
        - List of matched heuristic names for logging
    """
    risks = []
    matched_heuristics = []
    
    # Extract text for analysis
    text = clause.content.lower() + " " + clause.raw_excerpt.lower()
    
    # Assignment clause risks
    if any(term in key.lower() for term in ["assignment", "sublet", "transfer"]):
        # Check for broad assignment rights
        broad_assignment_pattern = (r"(freely|without\s+(landlord'?s\s+)?consent|may\s+assign\s+without).*?(assign|transfer|sublet)")
        if re.search(broad_assignment_pattern, text, re.IGNORECASE | re.DOTALL):
            risks.append(RiskFlag(
                clause_key=key,
                clause_name=key.replace("_", " ").title(),
                level=RiskLevel.HIGH,
                description="Tenant has unusually broad assignment or subletting rights without landlord consent.",
                source="clause_analysis",
                related_text=extract_relevant_text(clause.raw_excerpt, ["freely", "without consent", "assign", "transfer", "sublet"]),
                page_number=clause.page_number
            ))
            matched_heuristics.append("broad_assignment_rights")
            
        # Check for assignment restrictions
        restriction_pattern = r"(no|not|prohibit|restrict).*?\s+assign|sublet"
        consent_standard_pattern = r"consent.*?\s+not.*?\s+(unreasonably|arbitrarily).*?\s+(withheld|delayed|conditioned)"
        if re.search(restriction_pattern, text, re.IGNORECASE | re.DOTALL) and not re.search(consent_standard_pattern, text, re.IGNORECASE | re.DOTALL):
            risks.append(RiskFlag(
                clause_key=key,
                clause_name=key.replace("_", " ").title(),
                level=RiskLevel.MEDIUM,
                description="Assignment requires landlord consent with no standard for consent (may be arbitrarily withheld).",
                source="clause_analysis",
                related_text=extract_relevant_text(clause.raw_excerpt, ["consent", "assign", "sublet", "transfer"]),
                page_number=clause.page_number
            ))
            matched_heuristics.append("arbitrary_consent_standard")
    
    # Term and termination risks
    if any(term in key.lower() for term in ["term", "termination", "commencement"]):
        # Check for early termination without proper notice
        termination_pattern = r"(early|right\s+to).*\s+terminat"
        notice_pattern = r"notice.*?\s+(\d+|thirty|sixty|ninety).*?\s+(day|month|week)"
        if re.search(termination_pattern, text, re.IGNORECASE | re.DOTALL) and not re.search(notice_pattern, text, re.IGNORECASE | re.DOTALL):
            risks.append(RiskFlag(
                clause_key=key,
                clause_name=key.replace("_", " ").title(),
                level=RiskLevel.HIGH,
                description="Early termination right without clearly defined notice period.",
                source="clause_analysis",
                related_text=extract_relevant_text(clause.raw_excerpt, ["terminat", "early", "right to"]),
                page_number=clause.page_number
            ))
            matched_heuristics.append("unclear_termination_notice")
            
        # Check for uncertain commencement date
        uncertain_commencement_pattern = r"commencement.*?\s+(to\s+be|shall\s+be|will\s+be)\s+determin|commencement.*?\s+not\s+(yet)?\s+determin"
        if re.search(uncertain_commencement_pattern, text, re.IGNORECASE | re.DOTALL):
            risks.append(RiskFlag(
                clause_key=key,
                clause_name=key.replace("_", " ").title(),
                level=RiskLevel.MEDIUM,
                description="Commencement date is not clearly defined, creating uncertainty in lease term duration.",
                source="clause_analysis",
                related_text=extract_relevant_text(clause.raw_excerpt, ["commencement", "determin"]),
                page_number=clause.page_number
            ))
            matched_heuristics.append("uncertain_commencement")
    
    # Rent risks
    if any(term in key.lower() for term in ["rent", "payment", "base_rent"]):
        # Check for undefined rent escalations
        escalation_pattern = r"(increas|escalat|adjust)"
        amount_pattern = r"(\d+(\.\d+)?%|\d+\s+percent|\$\s*\d+)"
        if re.search(escalation_pattern, text, re.IGNORECASE | re.DOTALL) and not re.search(amount_pattern, text, re.IGNORECASE | re.DOTALL):
            risks.append(RiskFlag(
                clause_key=key,
                clause_name=key.replace("_", " ").title(),
                level=RiskLevel.HIGH,
                description="Rent escalation mentioned without specific amounts or percentages defined.",
                source="clause_analysis",
                related_text=extract_relevant_text(clause.raw_excerpt, ["increas", "escalat", "adjust"]),
                page_number=clause.page_number
            ))
            matched_heuristics.append("undefined_escalation")
            
        # Check for CPI escalations
        cpi_pattern = r"(CPI|consumer\s+price\s+index)"
        cap_pattern = r"(cap|maximum|not\s+to\s+exceed|ceiling)"
        if re.search(cpi_pattern, text, re.IGNORECASE | re.DOTALL) and not re.search(cap_pattern, text, re.IGNORECASE | re.DOTALL):
            risks.append(RiskFlag(
                clause_key=key,
                clause_name=key.replace("_", " ").title(),
                level=RiskLevel.MEDIUM,
                description="CPI rent escalation without a cap, creating potentially unlimited increases.",
                source="clause_analysis",
                related_text=extract_relevant_text(clause.raw_excerpt, ["CPI", "consumer price index"]),
                page_number=clause.page_number
            ))
            matched_heuristics.append("uncapped_cpi")
    
    # Insurance risks
    if any(term in key.lower() for term in ["insurance", "liability", "indemnity"]):
        # Check for missing insurance requirements
        coverage_pattern = r"(coverage|policy|limit|amount)"
        if len(text) < 200 or not re.search(coverage_pattern, text, re.IGNORECASE | re.DOTALL):
            risks.append(RiskFlag(
                clause_key=key,
                clause_name=key.replace("_", " ").title(),
                level=RiskLevel.HIGH,
                description="Insurance clause appears incomplete or lacks specific coverage requirements.",
                source="clause_analysis",
                related_text=clause.raw_excerpt[:200] + "..." if len(clause.raw_excerpt) > 200 else clause.raw_excerpt,
                page_number=clause.page_number
            ))
            matched_heuristics.append("incomplete_insurance")
            
        # Check for mutual waiver of subrogation
        subrogation_pattern = r"subrogation"
        mutual_waiver_pattern = r"(mutual|both\s+parties).*?\s+waiver.*?\s+subrogation"
        if re.search(subrogation_pattern, text, re.IGNORECASE | re.DOTALL) and not re.search(mutual_waiver_pattern, text, re.IGNORECASE | re.DOTALL):
            risks.append(RiskFlag(
                clause_key=key,
                clause_name=key.replace("_", " ").title(),
                level=RiskLevel.MEDIUM,
                description="No clear mutual waiver of subrogation specified, which may create insurance recovery issues.",
                source="clause_analysis",
                related_text=extract_relevant_text(clause.raw_excerpt, ["subrogation", "waiver"]),
                page_number=clause.page_number
            ))
            matched_heuristics.append("no_mutual_subrogation")
    
    # Use clause risks
    if any(term in key.lower() for term in ["use", "permitted_use"]):
        # Check for overly restrictive use
        restrictive_use_pattern = r"(only|solely|exclusively)\s+for"
        flexibility_pattern = r"(similar|other|additional|related)\s+(use|purpose)"
        if re.search(restrictive_use_pattern, text, re.IGNORECASE | re.DOTALL) and not re.search(flexibility_pattern, text, re.IGNORECASE | re.DOTALL):
            risks.append(RiskFlag(
                clause_key=key,
                clause_name=key.replace("_", " ").title(),
                level=RiskLevel.MEDIUM,
                description="Use clause is narrowly defined without flexibility for related or additional uses.",
                source="clause_analysis",
                related_text=extract_relevant_text(clause.raw_excerpt, ["only", "solely", "exclusively"]),
                page_number=clause.page_number
            ))
            matched_heuristics.append("restrictive_use")
    
    return risks, matched_heuristics


def analyze_retail_specific_risks(clauses: Dict[str, ClauseExtraction]) -> Tuple[List[RiskFlag], Dict[str, List[str]]]:
    """
    Analyze retail-specific risks.
    
    Args:
        clauses: Dictionary of extracted lease clauses
        
    Returns:
        Tuple of:
        - List of risk flags identified
        - Dictionary mapping clause keys to matched heuristic names
    """
    risks = []
    heuristics_by_clause = {}  # For tracking which heuristics matched in which clauses
    
    # Check for co-tenancy issues
    has_cotenancy = False
    for key, clause in clauses.items():
        text = clause.content.lower() + " " + clause.raw_excerpt.lower()
        matched_clause_heuristics = []
        
        # Co-tenancy risks
        if "co_tenancy" in key.lower() or "cotenancy" in key.lower() or re.search(r"co[\-\s]tenancy", text, re.IGNORECASE | re.DOTALL):
            has_cotenancy = True
            remedy_pattern = r"(terminat|reduc|abate|remedy)"
            if not re.search(remedy_pattern, text, re.IGNORECASE | re.DOTALL):
                risks.append(RiskFlag(
                    clause_key=key,
                    clause_name=key.replace("_", " ").title(),
                    level=RiskLevel.HIGH,
                    description="Co-tenancy clause lacks clear remedies if co-tenancy requirements are not satisfied.",
                    source="retail_analysis",
                    related_text=extract_relevant_text(clause.raw_excerpt, ["co-tenancy", "cotenancy"]),
                    page_number=clause.page_number
                ))
                matched_clause_heuristics.append("no_cotenancy_remedy")
            
        # Percentage rent risks
        percentage_rent_pattern = r"percentage\s+rent"
        percentage_pattern = r"(\d+(\.\d+)?%|\d+\s+percent)"
        if "percentage_rent" in key.lower() or re.search(percentage_rent_pattern, text, re.IGNORECASE | re.DOTALL):
            if not re.search(percentage_pattern, text, re.IGNORECASE | re.DOTALL):
                risks.append(RiskFlag(
                    clause_key=key,
                    clause_name=key.replace("_", " ").title(),
                    level=RiskLevel.MEDIUM,
                    description="Percentage rent mentioned without specific percentage defined.",
                    source="retail_analysis",
                    related_text=extract_relevant_text(clause.raw_excerpt, ["percentage rent"]),
                    page_number=clause.page_number
                ))
                matched_clause_heuristics.append("undefined_percentage_rent")
            
        # Operating hours risks
        hours_pattern = r"(operating|business)\s+hours"
        mall_hours_pattern = r"(mall|center|shopping).*?\s+hours"
        mandate_pattern = r"(must|shall|required|obligated)"
        if "operating_hours" in key.lower() or "hours_of_operation" in key.lower() or re.search(hours_pattern, text, re.IGNORECASE | re.DOTALL):
            if re.search(mall_hours_pattern, text, re.IGNORECASE | re.DOTALL) and re.search(mandate_pattern, text, re.IGNORECASE | re.DOTALL):
                risks.append(RiskFlag(
                    clause_key=key,
                    clause_name=key.replace("_", " ").title(),
                    level=RiskLevel.MEDIUM,
                    description="Tenant must maintain same operating hours as the shopping center, which may create staffing and operational issues.",
                    source="retail_analysis",
                    related_text=extract_relevant_text(clause.raw_excerpt, ["operating hours", "business hours", "mall", "center"]),
                    page_number=clause.page_number
                ))
                matched_clause_heuristics.append("mandatory_mall_hours")
            
        # Check for exclusivity
        exclusive_pattern = r"exclusive"
        tenant_exclusive_pattern = r"(tenant|lessee).*?\s+exclusive"
        retail_pattern = r"(retail|shopping center|mall)"
        if "exclusive" in key.lower() or re.search(exclusive_pattern, text, re.IGNORECASE | re.DOTALL):
            if not re.search(tenant_exclusive_pattern, text, re.IGNORECASE | re.DOTALL) and re.search(retail_pattern, text, re.IGNORECASE | re.DOTALL):
                risks.append(RiskFlag(
                    clause_key=key,
                    clause_name=key.replace("_", " ").title(),
                    level=RiskLevel.MEDIUM,
                    description="No exclusive use rights for retail tenant, allowing landlord to lease to direct competitors.",
                    source="retail_analysis", 
                    related_text=extract_relevant_text(clause.raw_excerpt, ["exclusive"]),
                    page_number=clause.page_number
                ))
                matched_clause_heuristics.append("no_tenant_exclusive")
        
        # Add any matched heuristics to the tracking dictionary
        if matched_clause_heuristics:
            heuristics_by_clause[key] = matched_clause_heuristics
    
    # Check for missing co-tenancy in retail lease
    use_text = ""
    for key, clause in clauses.items():
        if any(term in key.lower() for term in ["use", "permitted"]):
            use_text += clause.content.lower() + " " + clause.raw_excerpt.lower()
    
    if not has_cotenancy and re.search(r"(retail|store|shop|shopping center|mall)", use_text, re.IGNORECASE | re.DOTALL):
        risks.append(RiskFlag(
            clause_key="missing_cotenancy",
            clause_name="Missing Co-Tenancy",
            level=RiskLevel.HIGH,
            description="Retail lease appears to lack co-tenancy provisions, which could leave tenant vulnerable if key anchors or other tenants vacate.",
            source="retail_analysis",
            related_text="No co-tenancy clause found",
            page_number=None
        ))
        heuristics_by_clause["missing_cotenancy"] = ["missing_cotenancy_clause"]
    
    return risks, heuristics_by_clause


def analyze_office_specific_risks(clauses: Dict[str, ClauseExtraction]) -> Tuple[List[RiskFlag], Dict[str, List[str]]]:
    """
    Analyze office-specific risks.
    
    Args:
        clauses: Dictionary of extracted lease clauses
        
    Returns:
        Tuple of:
        - List of risk flags identified
        - Dictionary mapping clause keys to matched heuristic names
    """
    risks = []
    heuristics_by_clause = {}
    
    # Check for operating expense issues
    for key, clause in clauses.items():
        text = clause.content.lower() + " " + clause.raw_excerpt.lower()
        matched_clause_heuristics = []
        
        # Operating expense risks
        opex_pattern = r"operating\s+expenses"
        cap_pattern = r"(cap|ceiling|maximum|not\s+to\s+exceed)"
        if any(term in key.lower() for term in ["operating_expenses", "opex", "expense"]) or re.search(opex_pattern, text, re.IGNORECASE | re.DOTALL):
            if not re.search(cap_pattern, text, re.IGNORECASE | re.DOTALL):
                risks.append(RiskFlag(
                    clause_key=key,
                    clause_name=key.replace("_", " ").title(),
                    level=RiskLevel.MEDIUM,
                    description="No cap on operating expense increases, which may lead to unpredictable cost increases.",
                    source="office_analysis",
                    related_text=extract_relevant_text(clause.raw_excerpt, ["operating expense", "opex"]),
                    page_number=clause.page_number
                ))
                matched_clause_heuristics.append("no_opex_cap")
            
            audit_pattern = r"(audit|review|inspect|examin).*?\s+(books|records)"
            if not re.search(audit_pattern, text, re.IGNORECASE | re.DOTALL):
                risks.append(RiskFlag(
                    clause_key=key,
                    clause_name=key.replace("_", " ").title(),
                    level=RiskLevel.MEDIUM,
                    description="No audit rights for operating expenses, which may prevent tenant from verifying charges.",
                    source="office_analysis",
                    related_text=extract_relevant_text(clause.raw_excerpt, ["operating expense", "opex"]),
                    page_number=clause.page_number
                ))
                matched_clause_heuristics.append("no_audit_rights")
            
        # Measurement method risks
        sqft_pattern = r"(square\s+feet|sq\.?\s*ft\.?|area|rentable)"
        measurement_std_pattern = r"(BOMA|REBNY|measurement\s+standard)"
        if any(term in key.lower() for term in ["square_feet", "sqft", "area", "premises"]) or re.search(sqft_pattern, text, re.IGNORECASE | re.DOTALL):
            if not re.search(measurement_std_pattern, text, re.IGNORECASE | re.DOTALL):
                risks.append(RiskFlag(
                    clause_key=key,
                    clause_name=key.replace("_", " ").title(),
                    level=RiskLevel.MEDIUM,
                    description="No specific measurement standard defined for square footage, which may create discrepancies in rentable area calculations.",
                    source="office_analysis",
                    related_text=extract_relevant_text(clause.raw_excerpt, ["square feet", "sqft", "area", "rentable"]),
                    page_number=clause.page_number
                ))
                matched_clause_heuristics.append("no_measurement_standard")
            
        # Tenant improvement risks
        ti_pattern = r"(tenant\s+improvement|allowance|build[- ]out)"
        amount_pattern = r"(\$\s*\d+|\d+\s+dollars|per\s+square\s+foot)"
        if any(term in key.lower() for term in ["improvement", "allowance", "buildout"]) or re.search(ti_pattern, text, re.IGNORECASE | re.DOTALL):
            if not re.search(amount_pattern, text, re.IGNORECASE | re.DOTALL):
                risks.append(RiskFlag(
                    clause_key=key,
                    clause_name=key.replace("_", " ").title(),
                    level=RiskLevel.MEDIUM,
                    description="Tenant improvement allowance lacks specific dollar amount or calculation method.",
                    source="office_analysis",
                    related_text=extract_relevant_text(clause.raw_excerpt, ["improvement", "allowance", "buildout"]),
                    page_number=clause.page_number
                ))
                matched_clause_heuristics.append("undefined_ti_allowance")
                
        # Add any matched heuristics to the tracking dictionary
        if matched_clause_heuristics:
            heuristics_by_clause[key] = matched_clause_heuristics
    
    return risks, heuristics_by_clause


def analyze_industrial_specific_risks(clauses: Dict[str, ClauseExtraction]) -> Tuple[List[RiskFlag], Dict[str, List[str]]]:
    """
    Analyze industrial-specific risks.
    
    Args:
        clauses: Dictionary of extracted lease clauses
        
    Returns:
        Tuple of:
        - List of risk flags identified
        - Dictionary mapping clause keys to matched heuristic names
    """
    risks = []
    heuristics_by_clause = {}
    
    # Check for environmental and hazardous materials issues
    for key, clause in clauses.items():
        text = clause.content.lower() + " " + clause.raw_excerpt.lower()
        matched_clause_heuristics = []
        
        # Environmental risks
        env_pattern = r"environmental"
        tenant_resp_pattern = r"(tenant|lessee).*?\s+(respons|liability|remediat|clean)"
        preexisting_pattern = r"(pre.*?exist|prior|existing)"
        if "environmental" in key.lower() or re.search(env_pattern, text, re.IGNORECASE | re.DOTALL):
            if re.search(tenant_resp_pattern, text, re.IGNORECASE | re.DOTALL) and re.search(preexisting_pattern, text, re.IGNORECASE | re.DOTALL):
                risks.append(RiskFlag(
                    clause_key=key,
                    clause_name=key.replace("_", " ").title(),
                    level=RiskLevel.HIGH,
                    description="Tenant may be responsible for pre-existing environmental conditions, which creates significant liability.",
                    source="industrial_analysis",
                    related_text=extract_relevant_text(clause.raw_excerpt, ["environmental", "tenant", "lessee", "responsibility", "liability"]),
                    page_number=clause.page_number
                ))
                matched_clause_heuristics.append("tenant_preexisting_env_liability")
            
        # Hazardous materials risks
        hazmat_pattern = r"hazardous\s+materials"
        landlord_rep_pattern = r"(landlord|lessor).*?\s+(represent|warrant|disclos)"
        if "hazardous" in key.lower() or "hazmat" in key.lower() or re.search(hazmat_pattern, text, re.IGNORECASE | re.DOTALL):
            if not re.search(landlord_rep_pattern, text, re.IGNORECASE | re.DOTALL):
                risks.append(RiskFlag(
                    clause_key=key,
                    clause_name=key.replace("_", " ").title(),
                    level=RiskLevel.HIGH,
                    description="No landlord representations regarding hazardous materials, which creates uncertainty about site conditions.",
                    source="industrial_analysis",
                    related_text=extract_relevant_text(clause.raw_excerpt, ["hazardous", "materials"]),
                    page_number=clause.page_number
                ))
                matched_clause_heuristics.append("no_hazmat_representations")
                
            indemnify_pattern = r"(indemnif|hold\s+harmless).*?\s+(landlord|lessor)"
            except_pattern = r"except.*?\s+(pre.*?exist|prior|existing)"
            if re.search(indemnify_pattern, text, re.IGNORECASE | re.DOTALL) and not re.search(except_pattern, text, re.IGNORECASE | re.DOTALL):
                risks.append(RiskFlag(
                    clause_key=key,
                    clause_name=key.replace("_", " ").title(),
                    level=RiskLevel.HIGH,
                    description="Tenant must indemnify landlord for hazardous materials issues without exception for pre-existing conditions, creating potentially unlimited liability.",
                    source="industrial_analysis",
                    related_text=extract_relevant_text(clause.raw_excerpt, ["indemnif", "hold harmless", "hazardous"]),
                    page_number=clause.page_number
                ))
                matched_clause_heuristics.append("unlimited_hazmat_indemnity")
            
        # ADA compliance risks
        ada_pattern = r"(ADA|Americans\s+with\s+Disabilities\s+Act|accessibility)"
        tenant_ada_pattern = r"(tenant|lessee).*?\s+(respons|comply|compliance)"
        existing_pattern = r"(existing|current|premises)"
        if re.search(ada_pattern, text, re.IGNORECASE | re.DOTALL):
            if re.search(tenant_ada_pattern, text, re.IGNORECASE | re.DOTALL) and re.search(existing_pattern, text, re.IGNORECASE | re.DOTALL):
                risks.append(RiskFlag(
                    clause_key=key,
                    clause_name=key.replace("_", " ").title(),
                    level=RiskLevel.MEDIUM,
                    description="Tenant responsible for ADA compliance of existing premises, which could create significant retrofit liability.",
                    source="industrial_analysis",
                    related_text=extract_relevant_text(clause.raw_excerpt, ["ADA", "Americans with Disabilities", "accessibility"]),
                    page_number=clause.page_number
                ))
                matched_clause_heuristics.append("tenant_ada_liability")
                
        # Add any matched heuristics to the tracking dictionary
        if matched_clause_heuristics:
            heuristics_by_clause[key] = matched_clause_heuristics
    
    return risks, heuristics_by_clause


def analyze_cross_clause_risks(clauses: Dict[str, ClauseExtraction], lease_type: LeaseType) -> Tuple[List[RiskFlag], Dict[str, List[str]]]:
    """
    Identify risks that span multiple clauses.
    
    Args:
        clauses: Dictionary of extracted lease clauses
        lease_type: Type of lease
        
    Returns:
        Tuple of:
        - List of risk flags identified
        - Dictionary mapping clause keys to matched heuristic names
    """
    risks = []
    heuristics_by_clause = {}
    
    # Check for repair responsibility vs. insurance coverage mismatch
    repair_responsibility = "unknown"
    repair_clause_key = None
    
    for key, clause in clauses.items():
        if any(term in key.lower() for term in ["maintenance", "repair"]):
            text = clause.content.lower() + " " + clause.raw_excerpt.lower()
            tenant_repair_pattern = r"(tenant|lessee).*?\s+(respons|shall|must).*?\s+(repair|maintain)"
            structural_pattern = r"(structural|roof|foundation|exterior)"
            landlord_repair_pattern = r"(landlord|lessor).*?\s+(respons|shall|must).*?\s+(repair|maintain)"
            
            if re.search(tenant_repair_pattern, text, re.IGNORECASE | re.DOTALL) and re.search(structural_pattern, text, re.IGNORECASE | re.DOTALL):
                repair_responsibility = "tenant"
                repair_clause_key = key
                break
            elif re.search(landlord_repair_pattern, text, re.IGNORECASE | re.DOTALL) and re.search(structural_pattern, text, re.IGNORECASE | re.DOTALL):
                repair_responsibility = "landlord"
                repair_clause_key = key
                break
    
    insurance_coverage = "unknown"
    insurance_clause_key = None
    
    for key, clause in clauses.items():
        if any(term in key.lower() for term in ["insurance", "liability"]):
            text = clause.content.lower() + " " + clause.raw_excerpt.lower()
            property_ins_pattern = r"(property|casualty|all[\-\s]risk|fire).*?\s+insurance"
            tenant_ins_pattern = r"(tenant|lessee).*?\s+(shall|must|will|to\s+maintain)"
            landlord_ins_pattern = r"(landlord|lessor).*?\s+(shall|must|will|to\s+maintain)"
            
            if re.search(property_ins_pattern, text, re.IGNORECASE | re.DOTALL) and re.search(tenant_ins_pattern, text, re.IGNORECASE | re.DOTALL):
                insurance_coverage = "tenant"
                insurance_clause_key = key
                break
            elif re.search(property_ins_pattern, text, re.IGNORECASE | re.DOTALL) and re.search(landlord_ins_pattern, text, re.IGNORECASE | re.DOTALL):
                insurance_coverage = "landlord"
                insurance_clause_key = key
                break
    
    if repair_responsibility == "tenant" and insurance_coverage == "landlord":
        risks.append(RiskFlag(
            clause_key="cross_clause_risk",
            clause_name="Repair/Insurance Mismatch",
            level=RiskLevel.HIGH,
            description="Tenant has responsibility for structural repairs but landlord maintains the property insurance, creating potential coverage gaps.",
            source="cross_clause_analysis",
            related_text="Multiple clauses affected"
        ))
        
        # Add to heuristics tracking
        if repair_clause_key:
            heuristics_by_clause[repair_clause_key] = heuristics_by_clause.get(repair_clause_key, []) + ["repair_insurance_mismatch"]
        if insurance_clause_key:
            heuristics_by_clause[insurance_clause_key] = heuristics_by_clause.get(insurance_clause_key, []) + ["repair_insurance_mismatch"]
    
    # Check for tenant termination rights vs. landlord's remedies for default
    tenant_termination = False
    termination_clause_key = None
    
    for key, clause in clauses.items():
        if any(term in key.lower() for term in ["term", "termination"]):
            text = clause.content.lower() + " " + clause.raw_excerpt.lower()
            tenant_term_pattern = r"(tenant|lessee).*?\s+(right|option|may).*?\s+terminat"
            
            if re.search(tenant_term_pattern, text, re.IGNORECASE | re.DOTALL):
                tenant_termination = True
                termination_clause_key = key
                break
    
    landlord_remedies_accelerated = False
    default_clause_key = None
    
    for key, clause in clauses.items():
        if any(term in key.lower() for term in ["default", "remedies"]):
            text = clause.content.lower() + " " + clause.raw_excerpt.lower()
            accel_pattern = r"(landlord|lessor).*?\s+(right|may|shall|entitled).*?\s+(accelerat|due|payable)"
            rent_pattern = r"(rent|payment|amount)"
            
            if re.search(accel_pattern, text, re.IGNORECASE | re.DOTALL) and re.search(rent_pattern, text, re.IGNORECASE | re.DOTALL):
                landlord_remedies_accelerated = True
                default_clause_key = key
                break
    
    if tenant_termination and landlord_remedies_accelerated:
        risks.append(RiskFlag(
            clause_key="cross_clause_risk",
            clause_name="Termination vs. Acceleration",
            level=RiskLevel.MEDIUM,
            description="Tenant has termination rights but landlord can accelerate rent upon default, potentially creating contradictory remedies.",
            source="cross_clause_analysis",
            related_text="Multiple clauses affected"
        ))
        
        # Add to heuristics tracking
        if termination_clause_key:
            heuristics_by_clause[termination_clause_key] = heuristics_by_clause.get(termination_clause_key, []) + ["termination_acceleration_conflict"]
        if default_clause_key:
            heuristics_by_clause[default_clause_key] = heuristics_by_clause.get(default_clause_key, []) + ["termination_acceleration_conflict"]
    
    return risks, heuristics_by_clause


def extract_relevant_text(text: str, keywords: List[str], context_chars: int = 30) -> str:
    """
    Extract the most relevant portion of text containing keywords.
    
    Args:
        text: The full text to extract from
        keywords: List of keywords to search for
        context_chars: Number of characters around keyword for context
        
    Returns:
        A string with the most relevant portion of text
    """
    if not text or not keywords:
        return ""
    
    text_lower = text.lower()
    best_pos = -1
    best_keyword = ""
    
    # Find the first occurrence of any keyword
    for keyword in keywords:
        pos = text_lower.find(keyword)
        if pos != -1 and (best_pos == -1 or pos < best_pos):
            best_pos = pos
            best_keyword = keyword
    
    if best_pos == -1:
        return text[:100] + "..."  # No keywords found, return first 100 chars
    
    # Extract context around the keyword
    start = max(0, best_pos - context_chars)
    end = min(len(text), best_pos + len(best_keyword) + context_chars)
    
    # Adjust to include whole words
    while start > 0 and text[start] != ' ':
        start -= 1
    
    while end < len(text) and text[end] != ' ':
        end += 1
    
    extract = text[start:end].strip()
    
    # Add ellipses to indicate truncation
    if start > 0:
        extract = "..." + extract
    if end < len(text):
        extract = extract + "..."
    
    return extract


def deduplicate_risks(risks: List[RiskFlag]) -> List[RiskFlag]:
    """
    Remove duplicate risk flags.
    
    Args:
        risks: List of risk flags to deduplicate
        
    Returns:
        A list with unique risk flags
    """
    seen = set()
    unique_risks = []
    
    for risk in risks:
        # Create a tuple of key fields to check for duplicates
        key = (risk.clause_key, risk.description)
        
        if key not in seen:
            seen.add(key)
            unique_risks.append(risk)
    
    return unique_risks

# TODO: Enhance the system with semantic similarity or embedding-based clause detection
# This would involve:
# 1. Creating embeddings for each clause using a model like BERT or OpenAI's text-embedding models
# 2. Computing similarity between clauses and common clause templates
# 3. Using a threshold to determine if a clause matches a category 
# 4. Potentially training a specialized model on lease data to better recognize clause types
