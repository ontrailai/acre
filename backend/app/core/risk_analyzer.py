from typing import Dict, List, Any, Tuple
from app.schemas import LeaseType, ClauseExtraction, RiskLevel, RiskFlag
from app.utils.logger import logger
import re

def analyze_risks(clauses: Dict[str, ClauseExtraction], lease_type: LeaseType) -> Tuple[List[RiskFlag], List[str]]:
    """
    Analyze lease clauses for potential risks.
    Returns:
    - A list of risk flags with details
    - A list of missing clauses
    """
    try:
        # Initialize results
        risk_flags = []
        missing_clauses = []
        
        # Check for missing essential clauses
        missing_clauses = check_missing_essential_clauses(clauses, lease_type)
        
        # Analyze existing clauses for risks
        for key, clause in clauses.items():
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
            
            # Then, perform additional risk analysis based on specialized checks
            additional_risks = analyze_clause_risks(key, clause, lease_type)
            risk_flags.extend(additional_risks)
        
        # Add lease-type specific risk analysis
        if lease_type == LeaseType.RETAIL:
            retail_risks = analyze_retail_specific_risks(clauses)
            risk_flags.extend(retail_risks)
        elif lease_type == LeaseType.OFFICE:
            office_risks = analyze_office_specific_risks(clauses)
            risk_flags.extend(office_risks)
        elif lease_type == LeaseType.INDUSTRIAL:
            industrial_risks = analyze_industrial_specific_risks(clauses)
            risk_flags.extend(industrial_risks)
        
        # Check for cross-clause risks (issues that span multiple clauses)
        cross_clause_risks = analyze_cross_clause_risks(clauses, lease_type)
        risk_flags.extend(cross_clause_risks)
        
        # De-duplicate risk flags
        risk_flags = deduplicate_risks(risk_flags)
        
        logger.info(f"Risk analysis complete. Found {len(risk_flags)} risks and {len(missing_clauses)} missing clauses")
        return risk_flags, missing_clauses
        
    except Exception as e:
        logger.error(f"Error analyzing risks: {str(e)}")
        return [], []


def check_missing_essential_clauses(clauses: Dict[str, ClauseExtraction], lease_type: LeaseType) -> List[str]:
    """Check for missing essential clauses based on lease type"""
    # Define essential clauses for all lease types
    essential_clauses = {
        "premises": ["premises", "leased_premises", "demised_premises"],
        "term": ["term", "commencement", "expiration", "lease_term"],
        "rent": ["rent", "payment", "base_rent", "minimum_rent"],
        "maintenance": ["maintenance", "repair", "alteration"],
        "use": ["use", "permitted_use", "prohibited_use"],
        "assignment": ["assignment", "sublet", "transfer", "subletting"],
        "insurance": ["insurance", "liability", "indemnity", "indemnification"],
        "default": ["default", "remedies", "events_of_default"]
    }
    
    # Add lease-type specific essential clauses
    if lease_type == LeaseType.RETAIL:
        essential_clauses.update({
            "operating_hours": ["operating_hours", "hours_of_operation", "business_hours"],
            "common_area": ["cam", "common_area", "common_area_maintenance", "operating_expenses"],
            "percentage_rent": ["percentage_rent", "overage_rent"]
        })
    elif lease_type == LeaseType.OFFICE:
        essential_clauses.update({
            "building_services": ["building_services", "services"],
            "operating_expenses": ["operating_expenses", "opex", "expenses"],
            "tenant_improvements": ["improvements", "tenant_improvements", "allowance"]
        })
    elif lease_type == LeaseType.INDUSTRIAL:
        essential_clauses.update({
            "environmental": ["environmental", "compliance", "environmental_compliance"],
            "hazardous_materials": ["hazardous", "hazmat", "hazardous_materials"]
        })
    
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
            missing.append(category.replace("_", " ").title())
    
    return missing


def analyze_clause_risks(key: str, clause: ClauseExtraction, lease_type: LeaseType) -> List[RiskFlag]:
    """Analyze a single clause for potential risks"""
    risks = []
    
    # Extract text for analysis
    text = clause.content.lower() + " " + clause.raw_excerpt.lower()
    
    # Assignment clause risks
    if any(term in key.lower() for term in ["assignment", "sublet", "transfer"]):
        # Check for broad assignment rights
        if (re.search(r"freely", text) and re.search(r"(assign|transfer|sublet)", text)) or \
           (re.search(r"without(\s+landlord'?s)?\s+consent", text) and re.search(r"(assign|transfer|sublet)", text)):
            risks.append(RiskFlag(
                clause_key=key,
                clause_name=key.replace("_", " ").title(),
                level=RiskLevel.HIGH,
                description="Tenant has unusually broad assignment or subletting rights without landlord consent.",
                source="clause_analysis",
                related_text=extract_relevant_text(clause.raw_excerpt, ["freely", "without consent", "assign", "transfer", "sublet"]),
                page_number=clause.page_number
            ))
            
        # Check for assignment restrictions
        elif re.search(r"(no|not|prohibit|restrict).*?\s+assign", text) or re.search(r"(no|not|prohibit|restrict).*?\s+sublet", text):
            if not re.search(r"consent.*?\s+not.*?\s+(unreasonably|arbitrarily).*?\s+(withheld|delayed|conditioned)", text):
                risks.append(RiskFlag(
                    clause_key=key,
                    clause_name=key.replace("_", " ").title(),
                    level=RiskLevel.MEDIUM,
                    description="Assignment requires landlord consent with no standard for consent (may be arbitrarily withheld).",
                    source="clause_analysis",
                    related_text=extract_relevant_text(clause.raw_excerpt, ["consent", "assign", "sublet", "transfer"]),
                    page_number=clause.page_number
                ))
    
    # Term and termination risks
    if any(term in key.lower() for term in ["term", "termination", "commencement"]):
        # Check for early termination without proper notice
        if re.search(r"(early|right\s+to).*\s+terminat", text) and not re.search(r"notice.*?\s+(\d+|thirty|sixty|ninety).*?\s+(day|month|week)", text):
            risks.append(RiskFlag(
                clause_key=key,
                clause_name=key.replace("_", " ").title(),
                level=RiskLevel.HIGH,
                description="Early termination right without clearly defined notice period.",
                source="clause_analysis",
                related_text=extract_relevant_text(clause.raw_excerpt, ["terminat", "early", "right to"]),
                page_number=clause.page_number
            ))
            
        # Check for uncertain commencement date
        if re.search(r"commencement.*?\s+to\s+be\s+determin", text) or re.search(r"commencement.*?\s+not\s+yet\s+determin", text):
            risks.append(RiskFlag(
                clause_key=key,
                clause_name=key.replace("_", " ").title(),
                level=RiskLevel.MEDIUM,
                description="Commencement date is not clearly defined, creating uncertainty in lease term duration.",
                source="clause_analysis",
                related_text=extract_relevant_text(clause.raw_excerpt, ["commencement", "determin"]),
                page_number=clause.page_number
            ))
    
    # Rent risks
    if any(term in key.lower() for term in ["rent", "payment", "base_rent"]):
        # Check for undefined rent escalations
        if re.search(r"(increas|escalat|adjust)", text) and not re.search(r"(\d+(\.\d+)?%|\d+\s+percent|\$\s*\d+)", text):
            risks.append(RiskFlag(
                clause_key=key,
                clause_name=key.replace("_", " ").title(),
                level=RiskLevel.HIGH,
                description="Rent escalation mentioned without specific amounts or percentages defined.",
                source="clause_analysis",
                related_text=extract_relevant_text(clause.raw_excerpt, ["increas", "escalat", "adjust"]),
                page_number=clause.page_number
            ))
            
        # Check for CPI escalations
        if re.search(r"(CPI|consumer\s+price\s+index)", text) and not re.search(r"(cap|maximum|not\s+to\s+exceed|ceiling)", text):
            risks.append(RiskFlag(
                clause_key=key,
                clause_name=key.replace("_", " ").title(),
                level=RiskLevel.MEDIUM,
                description="CPI rent escalation without a cap, creating potentially unlimited increases.",
                source="clause_analysis",
                related_text=extract_relevant_text(clause.raw_excerpt, ["CPI", "consumer price index"]),
                page_number=clause.page_number
            ))
    
    # Insurance risks
    if any(term in key.lower() for term in ["insurance", "liability", "indemnity"]):
        # Check for missing insurance requirements
        if len(text) < 200 or not re.search(r"(coverage|policy|limit|amount)", text):
            risks.append(RiskFlag(
                clause_key=key,
                clause_name=key.replace("_", " ").title(),
                level=RiskLevel.HIGH,
                description="Insurance clause appears incomplete or lacks specific coverage requirements.",
                source="clause_analysis",
                related_text=clause.raw_excerpt[:200] + "..." if len(clause.raw_excerpt) > 200 else clause.raw_excerpt,
                page_number=clause.page_number
            ))
            
        # Check for mutual waiver of subrogation
        if re.search(r"subrogation", text) and not re.search(r"mutual.*?\s+waiver.*?\s+subrogation", text):
            risks.append(RiskFlag(
                clause_key=key,
                clause_name=key.replace("_", " ").title(),
                level=RiskLevel.MEDIUM,
                description="No clear mutual waiver of subrogation specified, which may create insurance recovery issues.",
                source="clause_analysis",
                related_text=extract_relevant_text(clause.raw_excerpt, ["subrogation", "waiver"]),
                page_number=clause.page_number
            ))
    
    # Use clause risks
    if any(term in key.lower() for term in ["use", "permitted_use"]):
        # Check for overly restrictive use
        if re.search(r"(only|solely|exclusively)\s+for", text) and not re.search(r"(similar|other|additional|related)\s+(use|purpose)", text):
            risks.append(RiskFlag(
                clause_key=key,
                clause_name=key.replace("_", " ").title(),
                level=RiskLevel.MEDIUM,
                description="Use clause is narrowly defined without flexibility for related or additional uses.",
                source="clause_analysis",
                related_text=extract_relevant_text(clause.raw_excerpt, ["only", "solely", "exclusively"]),
                page_number=clause.page_number
            ))
    
    return risks


def analyze_retail_specific_risks(clauses: Dict[str, ClauseExtraction]) -> List[RiskFlag]:
    """Analyze retail-specific risks"""
    risks = []
    
    # Check for co-tenancy issues
    has_cotenancy = False
    for key, clause in clauses.items():
        text = clause.content.lower() + " " + clause.raw_excerpt.lower()
        
        # Co-tenancy risks
        if "co_tenancy" in key.lower() or "cotenancy" in key.lower() or re.search(r"co[\-\s]tenancy", text):
            has_cotenancy = True
            if not re.search(r"(terminat|reduc|abate|remedy)", text):
                risks.append(RiskFlag(
                    clause_key=key,
                    clause_name=key.replace("_", " ").title(),
                    level=RiskLevel.HIGH,
                    description="Co-tenancy clause lacks clear remedies if co-tenancy requirements are not satisfied.",
                    source="retail_analysis",
                    related_text=extract_relevant_text(clause.raw_excerpt, ["co-tenancy", "cotenancy"]),
                    page_number=clause.page_number
                ))
            
        # Percentage rent risks
        if "percentage_rent" in key.lower() or re.search(r"percentage\s+rent", text):
            if not re.search(r"(\d+(\.\d+)?%|\d+\s+percent)", text):
                risks.append(RiskFlag(
                    clause_key=key,
                    clause_name=key.replace("_", " ").title(),
                    level=RiskLevel.MEDIUM,
                    description="Percentage rent mentioned without specific percentage defined.",
                    source="retail_analysis",
                    related_text=extract_relevant_text(clause.raw_excerpt, ["percentage rent"]),
                    page_number=clause.page_number
                ))
            
        # Operating hours risks
        if "operating_hours" in key.lower() or "hours_of_operation" in key.lower() or re.search(r"(operating|business)\s+hours", text):
            if re.search(r"(mall|center|shopping).*?\s+hours", text) and re.search(r"(must|shall|required|obligated)", text):
                risks.append(RiskFlag(
                    clause_key=key,
                    clause_name=key.replace("_", " ").title(),
                    level=RiskLevel.MEDIUM,
                    description="Tenant must maintain same operating hours as the shopping center, which may create staffing and operational issues.",
                    source="retail_analysis",
                    related_text=extract_relevant_text(clause.raw_excerpt, ["operating hours", "business hours", "mall", "center"]),
                    page_number=clause.page_number
                ))
            
        # Check for exclusivity
        if "exclusive" in key.lower() or re.search(r"exclusive", text):
            if not re.search(r"(tenant|lessee).*?\s+exclusive", text) and re.search(r"(retail|shopping center|mall)", text):
                risks.append(RiskFlag(
                    clause_key=key,
                    clause_name=key.replace("_", " ").title(),
                    level=RiskLevel.MEDIUM,
                    description="No exclusive use rights for retail tenant, allowing landlord to lease to direct competitors.",
                    source="retail_analysis", 
                    related_text=extract_relevant_text(clause.raw_excerpt, ["exclusive"]),
                    page_number=clause.page_number
                ))
    
    # Check for missing co-tenancy in retail lease
    use_text = ""
    for key, clause in clauses.items():
        if any(term in key.lower() for term in ["use", "permitted"]):
            use_text += clause.content.lower() + " " + clause.raw_excerpt.lower()
    
    if not has_cotenancy and re.search(r"(retail|store|shop|shopping center|mall)", use_text):
        risks.append(RiskFlag(
            clause_key="missing_cotenancy",
            clause_name="Missing Co-Tenancy",
            level=RiskLevel.HIGH,
            description="Retail lease appears to lack co-tenancy provisions, which could leave tenant vulnerable if key anchors or other tenants vacate.",
            source="retail_analysis",
            related_text="No co-tenancy clause found",
            page_number=None
        ))
    
    return risks


def analyze_office_specific_risks(clauses: Dict[str, ClauseExtraction]) -> List[RiskFlag]:
    """Analyze office-specific risks"""
    risks = []
    
    # Check for operating expense issues
    for key, clause in clauses.items():
        text = clause.content.lower() + " " + clause.raw_excerpt.lower()
        
        # Operating expense risks
        if any(term in key.lower() for term in ["operating_expenses", "opex", "expense"]) or re.search(r"operating\s+expenses", text):
            if not re.search(r"(cap|ceiling|maximum|not\s+to\s+exceed)", text):
                risks.append(RiskFlag(
                    clause_key=key,
                    clause_name=key.replace("_", " ").title(),
                    level=RiskLevel.MEDIUM,
                    description="No cap on operating expense increases, which may lead to unpredictable cost increases.",
                    source="office_analysis",
                    related_text=extract_relevant_text(clause.raw_excerpt, ["operating expense", "opex"]),
                    page_number=clause.page_number
                ))
            
            if not re.search(r"(audit|review|inspect|examin).*?\s+(books|records)", text):
                risks.append(RiskFlag(
                    clause_key=key,
                    clause_name=key.replace("_", " ").title(),
                    level=RiskLevel.MEDIUM,
                    description="No audit rights for operating expenses, which may prevent tenant from verifying charges.",
                    source="office_analysis",
                    related_text=extract_relevant_text(clause.raw_excerpt, ["operating expense", "opex"]),
                    page_number=clause.page_number
                ))
            
        # Measurement method risks
        if any(term in key.lower() for term in ["square_feet", "sqft", "area", "premises"]) or re.search(r"(square\s+feet|sq\.?\s*ft\.?|area|rentable)", text):
            if not re.search(r"(BOMA|REBNY|measurement\s+standard)", text):
                risks.append(RiskFlag(
                    clause_key=key,
                    clause_name=key.replace("_", " ").title(),
                    level=RiskLevel.MEDIUM,
                    description="No specific measurement standard defined for square footage, which may create discrepancies in rentable area calculations.",
                    source="office_analysis",
                    related_text=extract_relevant_text(clause.raw_excerpt, ["square feet", "sqft", "area", "rentable"]),
                    page_number=clause.page_number
                ))
            
        # Tenant improvement risks
        if any(term in key.lower() for term in ["improvement", "allowance", "buildout"]) or re.search(r"(tenant\s+improvement|allowance|build[- ]out)", text):
            if not re.search(r"(\$\s*\d+|\d+\s+dollars|per\s+square\s+foot)", text):
                risks.append(RiskFlag(
                    clause_key=key,
                    clause_name=key.replace("_", " ").title(),
                    level=RiskLevel.MEDIUM,
                    description="Tenant improvement allowance lacks specific dollar amount or calculation method.",
                    source="office_analysis",
                    related_text=extract_relevant_text(clause.raw_excerpt, ["improvement", "allowance", "buildout"]),
                    page_number=clause.page_number
                ))
    
    return risks


def analyze_industrial_specific_risks(clauses: Dict[str, ClauseExtraction]) -> List[RiskFlag]:
    """Analyze industrial-specific risks"""
    risks = []
    
    # Check for environmental and hazardous materials issues
    for key, clause in clauses.items():
        text = clause.content.lower() + " " + clause.raw_excerpt.lower()
        
        # Environmental risks
        if "environmental" in key.lower() or re.search(r"environmental", text):
            if re.search(r"(tenant|lessee).*?\s+(respons|liability|remediat|clean)", text) and re.search(r"(pre.*?exist|prior|existing)", text):
                risks.append(RiskFlag(
                    clause_key=key,
                    clause_name=key.replace("_", " ").title(),
                    level=RiskLevel.HIGH,
                    description="Tenant may be responsible for pre-existing environmental conditions, which creates significant liability.",
                    source="industrial_analysis",
                    related_text=extract_relevant_text(clause.raw_excerpt, ["environmental", "tenant", "lessee", "responsibility", "liability"]),
                    page_number=clause.page_number
                ))
            
        # Hazardous materials risks
        if "hazardous" in key.lower() or "hazmat" in key.lower() or re.search(r"hazardous\s+materials", text):
            if not re.search(r"(landlord|lessor).*?\s+(represent|warrant|disclos)", text):
                risks.append(RiskFlag(
                    clause_key=key,
                    clause_name=key.replace("_", " ").title(),
                    level=RiskLevel.HIGH,
                    description="No landlord representations regarding hazardous materials, which creates uncertainty about site conditions.",
                    source="industrial_analysis",
                    related_text=extract_relevant_text(clause.raw_excerpt, ["hazardous", "materials"]),
                    page_number=clause.page_number
                ))
                
            if re.search(r"(indemnif|hold\s+harmless).*?\s+(landlord|lessor)", text) and not re.search(r"except.*?\s+(pre.*?exist|prior|existing)", text):
                risks.append(RiskFlag(
                    clause_key=key,
                    clause_name=key.replace("_", " ").title(),
                    level=RiskLevel.HIGH,
                    description="Tenant must indemnify landlord for hazardous materials issues without exception for pre-existing conditions, creating potentially unlimited liability.",
                    source="industrial_analysis",
                    related_text=extract_relevant_text(clause.raw_excerpt, ["indemnif", "hold harmless", "hazardous"]),
                    page_number=clause.page_number
                ))
            
        # ADA compliance risks
        if re.search(r"(ADA|Americans\s+with\s+Disabilities\s+Act|accessibility)", text):
            if re.search(r"(tenant|lessee).*?\s+(respons|comply|compliance)", text) and re.search(r"(existing|current|premises)", text):
                risks.append(RiskFlag(
                    clause_key=key,
                    clause_name=key.replace("_", " ").title(),
                    level=RiskLevel.MEDIUM,
                    description="Tenant responsible for ADA compliance of existing premises, which could create significant retrofit liability.",
                    source="industrial_analysis",
                    related_text=extract_relevant_text(clause.raw_excerpt, ["ADA", "Americans with Disabilities", "accessibility"]),
                    page_number=clause.page_number
                ))
    
    return risks


def analyze_cross_clause_risks(clauses: Dict[str, ClauseExtraction], lease_type: LeaseType) -> List[RiskFlag]:
    """Identify risks that span multiple clauses"""
    risks = []
    
    # Check for repair responsibility vs. insurance coverage mismatch
    repair_responsibility = "unknown"
    for key, clause in clauses.items():
        if any(term in key.lower() for term in ["maintenance", "repair"]):
            text = clause.content.lower() + " " + clause.raw_excerpt.lower()
            if re.search(r"(tenant|lessee).*?\s+(respons|shall|must).*?\s+(repair|maintain)", text) and \
               re.search(r"(structural|roof|foundation|exterior)", text):
                repair_responsibility = "tenant"
                break
            elif re.search(r"(landlord|lessor).*?\s+(respons|shall|must).*?\s+(repair|maintain)", text) and \
                 re.search(r"(structural|roof|foundation|exterior)", text):
                repair_responsibility = "landlord"
                break
    
    insurance_coverage = "unknown"
    for key, clause in clauses.items():
        if any(term in key.lower() for term in ["insurance", "liability"]):
            text = clause.content.lower() + " " + clause.raw_excerpt.lower()
            if re.search(r"(property|casualty|all[\-\s]risk|fire).*?\s+insurance", text) and \
               re.search(r"(tenant|lessee).*?\s+(shall|must|will|to\s+maintain)", text):
                insurance_coverage = "tenant"
                break
            elif re.search(r"(property|casualty|all[\-\s]risk|fire).*?\s+insurance", text) and \
                 re.search(r"(landlord|lessor).*?\s+(shall|must|will|to\s+maintain)", text):
                insurance_coverage = "landlord"
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
    
    # Check for tenant termination rights vs. landlord's remedies for default
    tenant_termination = False
    for key, clause in clauses.items():
        if any(term in key.lower() for term in ["term", "termination"]):
            text = clause.content.lower() + " " + clause.raw_excerpt.lower()
            if re.search(r"(tenant|lessee).*?\s+(right|option|may).*?\s+terminat", text):
                tenant_termination = True
                break
    
    landlord_remedies_accelerated = False
    for key, clause in clauses.items():
        if any(term in key.lower() for term in ["default", "remedies"]):
            text = clause.content.lower() + " " + clause.raw_excerpt.lower()
            if re.search(r"(landlord|lessor).*?\s+(right|may|shall|entitled).*?\s+(accelerat|due|payable)", text) and \
               re.search(r"(rent|payment|amount)", text):
                landlord_remedies_accelerated = True
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
    
    return risks


def extract_relevant_text(text: str, keywords: List[str], context_chars: int = 20) -> str:
    """Extract the most relevant portion of text containing keywords"""
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
    """Remove duplicate risk flags"""
    seen = set()
    unique_risks = []
    
    for risk in risks:
        # Create a tuple of key fields to check for duplicates
        key = (risk.clause_key, risk.description)
        
        if key not in seen:
            seen.add(key)
            unique_risks.append(risk)
    
    return unique_risks
