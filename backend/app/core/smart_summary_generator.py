from typing import Dict, Any, Tuple, List
from app.schemas import LeaseType, SummaryStyle, ClauseExtraction
from app.utils.logger import logger

def generate_summary(
    clauses: Dict[str, ClauseExtraction],
    lease_type: LeaseType,
    summary_style: SummaryStyle
) -> Tuple[str, Dict[str, Any], Dict[str, float]]:
    """
    Generate a human-readable lease summary in Markdown format.
    Returns:
    - Markdown summary
    - Traceability information
    - Confidence scores
    """
    try:
        # Check if clauses is empty and provide a template summary
        if not clauses:
            logger.warning("No clauses were extracted, generating a basic template summary")
            return generate_empty_summary(lease_type), {}, {}
            
        # Extract summary sections based on lease type
        if lease_type == LeaseType.RETAIL:
            sections = generate_retail_summary(clauses, summary_style)
        elif lease_type == LeaseType.OFFICE:
            sections = generate_office_summary(clauses, summary_style)
        elif lease_type == LeaseType.INDUSTRIAL:
            sections = generate_industrial_summary(clauses, summary_style)
        else:
            sections = generate_default_summary(clauses, summary_style)
            
        # Build Markdown summary
        markdown = ""
        traceability = {}
        confidence_scores = {}
        
        # Add title
        markdown += f"# {lease_type.capitalize()} Lease Summary\n\n"
        
        # Add each section
        for section_title, section_content in sections.items():
            markdown += f"## {section_title}\n\n"
            if isinstance(section_content, dict):
                for key, clause_data in section_content.items():
                    if isinstance(clause_data, dict):
                        # Create a unique identifier for this clause
                        clause_id = f"{section_title.lower().replace(' ', '_')}_{key.lower().replace(' ', '_')}"
                        
                        # Add section header with field_id for traceability
                        markdown += f"### {key.replace('_', ' ').title()}\n\n"
                        
                        # Use summary bullet if available, otherwise use content
                        summary_text = clause_data.get('summary_bullet') or clause_data.get('content', 'Not specified')
                        markdown += f"{summary_text}\n\n"
                        
                        # Add traceability info directly in the summary if in LEGAL style
                        if summary_style == SummaryStyle.LEGAL and clause_data.get('source_excerpt') and clause_data.get('page_number'):
                            markdown += f"*Source: Page {clause_data.get('page_number')} - \"{clause_data.get('source_excerpt')[:100]}...\"*\n\n"
                        
                        # Add risk flags directly in the section if in LEGAL style
                        if summary_style == SummaryStyle.LEGAL and clause_data.get('risk_tags'):
                            for risk in clause_data.get('risk_tags', []):
                                risk_level = risk.get('level', 'medium')
                                emoji = "🔴" if risk_level == "high" else "🟠" if risk_level == "medium" else "🟡"
                                markdown += f"{emoji} **Risk**: {risk.get('description', 'Potential risk')}\n\n"
                        
                        # Add needs review flag if uncertain
                        if clause_data.get('needs_review', False):
                            markdown += f"⚠️ *This clause needs review – AI confidence is low*\n\n"
                        
                        # Collect traceability info
                        page_number = clause_data.get('page_number')
                        page_range = clause_data.get('page_range')
                        raw_excerpt = clause_data.get('source_excerpt') or clause_data.get('raw_excerpt', '')
                        field_id = clause_data.get('field_id', clause_id)
                        
                        if raw_excerpt:
                            traceability[key] = {
                                "page_number": page_number,
                                "page_range": page_range,
                                "excerpt": raw_excerpt[:300] + "..." if len(raw_excerpt) > 300 else raw_excerpt,
                                "field_id": field_id
                            }
                            
                        # Collect confidence scores
                        confidence = clause_data.get('confidence_score') or clause_data.get('confidence', 0.0)
                        if confidence:
                            confidence_scores[key] = confidence
                    else:
                        markdown += f"- {key.replace('_', ' ').title()}: {clause_data}\n"
            else:
                markdown += f"{section_content}\n\n"
        
        # Add risk section at the end
        risk_markdown = extract_risk_section(clauses)
        markdown += f"## ⚠️ Risk Analysis\n\n{risk_markdown}\n\n"
        
        # Add missing clauses section
        missing_markdown = extract_missing_clauses(clauses)
        markdown += f"## ❗ Missing or Incomplete Clauses\n\n{missing_markdown}\n\n"
        
        # Add traceability section in LEGAL style
        if summary_style == SummaryStyle.LEGAL:
            traceability_markdown = "See hover-over highlights for clause sources and page numbers.\n\n"
            markdown += f"## 📍 Source References\n\n{traceability_markdown}\n\n"
        
        logger.info("Summary generation completed successfully")
        return markdown, traceability, confidence_scores
        
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}")
        # Provide a basic summary on error
        return f"# Lease Summary\n\nError generating full summary: {str(e)}", {}, {}
        

def generate_empty_summary(lease_type: LeaseType) -> str:
    """Generate a basic summary when no clauses were extracted"""
    
    markdown = f"# {lease_type.capitalize()} Lease Summary\n\n"
    
    markdown += "## ⚠️ Extraction Notice\n\n"
    markdown += "**No lease clauses could be automatically extracted from this document.**\n\n"
    markdown += "This could be due to one of the following reasons:\n\n"
    markdown += "- The document appears to be a lease template with placeholder values rather than a completed lease\n"
    markdown += "- The document format may be different from what the system typically processes\n"
    markdown += "- The scan quality may be affecting text extraction\n\n"
    
    markdown += "## 📋 Next Steps\n\n"
    markdown += "Consider the following options:\n\n"
    markdown += "1. **Use a completed lease document** instead of a template\n"
    markdown += "2. **Check scan quality** if this is a scanned document\n"
    markdown += "3. **Try a different file format** if available\n"
    markdown += "4. **Contact support** if you need assistance with this document\n\n"
    
    markdown += "## 🔍 Document Analysis\n\n"
    markdown += "The system detected what appears to be a lease document, but could not reliably extract specific clauses and terms.\n"
    markdown += "Manual review is recommended for this document.\n\n"
    
    markdown += "## 💡 Template Document Tips\n\n"
    markdown += "If this is a template document, here are some tips:\n\n"
    markdown += "- Complete the template with actual values before uploading\n"
    markdown += "- Replace all placeholder values like [DATE], [AMOUNT], etc. with real information\n"
    markdown += "- Ensure all signatures and exhibits are properly completed\n"
    markdown += "- Try scanning the document again with higher quality settings if it's a scanned document\n\n"
    
    return markdown


def generate_default_summary(clauses: Dict[str, ClauseExtraction], summary_style: SummaryStyle) -> Dict[str, Any]:
    """Generate a default summary for any lease type"""
    summary = {}
    
    # 1. Lease Overview
    summary["📄 Lease Overview"] = extract_overview_section(clauses, summary_style)
    
    # 2. Lease Term
    summary["📅 Lease Term"] = extract_term_section(clauses, summary_style)
    
    # 3. Rent & Payments
    summary["💰 Rent & Payments"] = extract_rent_section(clauses, summary_style)
    
    # 4. Additional Charges
    summary["📊 Additional Charges"] = extract_additional_charges_section(clauses, summary_style)
    
    # 5. Maintenance Responsibilities
    summary["🛠 Maintenance Responsibilities"] = extract_maintenance_section(clauses, summary_style)
    
    # 6. Use of Premises
    summary["🏢 Use of Premises"] = extract_use_section(clauses, summary_style)
    
    # 7. Assignment & Subletting
    summary["🔄 Assignment & Subletting"] = extract_assignment_section(clauses, summary_style)
    
    # 8. Insurance Requirements
    summary["🔐 Insurance Requirements"] = extract_insurance_section(clauses, summary_style)
    
    # 9. Casualty
    summary["🔥 Casualty"] = extract_casualty_section(clauses, summary_style)
    
    # 10. Eminent Domain
    summary["🏛 Eminent Domain"] = extract_eminent_domain_section(clauses, summary_style)
    
    # 11. Legal Clauses
    summary["⚖️ Legal Clauses"] = extract_legal_section(clauses, summary_style)
    
    # 12. Entry & Access
    summary["🚪 Entry & Access"] = extract_entry_section(clauses, summary_style)
    
    # 13. Miscellaneous
    summary["📜 Miscellaneous"] = extract_miscellaneous_section(clauses, summary_style)
    
    # Apply style formatting
    if summary_style == SummaryStyle.EXECUTIVE:
        summary = format_executive_style(summary)
    
    return summary


def generate_retail_summary(clauses: Dict[str, ClauseExtraction], summary_style: SummaryStyle) -> Dict[str, Any]:
    """Generate a summary specifically for retail leases"""
    summary = generate_default_summary(clauses, summary_style)
    
    # Add retail-specific sections
    retail_specific = {}
    
    # Co-Tenancy
    co_tenancy = extract_section_by_keywords(clauses, ["co_tenancy", "cotenancy"], summary_style)
    if co_tenancy:
        retail_specific["🛍️ Co-Tenancy"] = co_tenancy
        
    # Percentage Rent
    percentage_rent = extract_section_by_keywords(clauses, ["percentage_rent", "percentagerent"], summary_style)
    if percentage_rent:
        retail_specific["💲 Percentage Rent"] = percentage_rent
        
    # Operating Hours
    operating_hours = extract_section_by_keywords(clauses, ["operating_hours", "hours_of_operation"], summary_style)
    if operating_hours:
        retail_specific["🕒 Operating Hours"] = operating_hours
    
    # Exclusivity
    exclusivity = extract_section_by_keywords(clauses, ["exclusive", "exclusivity"], summary_style)
    if exclusivity:
        retail_specific["🔒 Exclusivity"] = exclusivity
    
    # Merge with standard summary, inserting after Use of Premises
    if retail_specific:
        result = {}
        for key, value in summary.items():
            result[key] = value
            if key == "🏢 Use of Premises":
                for retail_key, retail_value in retail_specific.items():
                    result[retail_key] = retail_value
    else:
        result = summary
        
    return result


def generate_office_summary(clauses: Dict[str, ClauseExtraction], summary_style: SummaryStyle) -> Dict[str, Any]:
    """Generate a summary specifically for office leases"""
    summary = generate_default_summary(clauses, summary_style)
    
    # Add office-specific sections
    office_specific = {}
    
    # Building Services
    building_services = extract_section_by_keywords(clauses, ["building_services", "services"], summary_style)
    if building_services:
        office_specific["🏙️ Building Services"] = building_services
        
    # Tenant Improvements
    tenant_improvements = extract_section_by_keywords(clauses, ["tenant_improvement", "improvements", "allowance"], summary_style)
    if tenant_improvements:
        office_specific["🔨 Tenant Improvements"] = tenant_improvements
    
    # Operating Expenses
    operating_expenses = extract_section_by_keywords(clauses, ["operating_expenses", "opex", "expenses"], summary_style)
    if operating_expenses:
        office_specific["💵 Operating Expenses"] = operating_expenses
    
    # Merge with standard summary, inserting after Maintenance Responsibilities
    if office_specific:
        result = {}
        for key, value in summary.items():
            result[key] = value
            if key == "🛠 Maintenance Responsibilities":
                for office_key, office_value in office_specific.items():
                    result[office_key] = office_value
    else:
        result = summary
        
    return result


def generate_industrial_summary(clauses: Dict[str, ClauseExtraction], summary_style: SummaryStyle) -> Dict[str, Any]:
    """Generate a summary specifically for industrial leases"""
    summary = generate_default_summary(clauses, summary_style)
    
    # Add industrial-specific sections
    industrial_specific = {}
    
    # Environmental
    environmental = extract_section_by_keywords(clauses, ["environmental", "compliance"], summary_style)
    if environmental:
        industrial_specific["🌱 Environmental"] = environmental
        
    # Hazardous Materials
    hazardous_materials = extract_section_by_keywords(clauses, ["hazardous", "hazmat"], summary_style)
    if hazardous_materials:
        industrial_specific["☢️ Hazardous Materials"] = hazardous_materials
    
    # ADA Compliance
    ada_compliance = extract_section_by_keywords(clauses, ["ada", "disabilities", "accessibility"], summary_style)
    if ada_compliance:
        industrial_specific["♿ ADA Compliance"] = ada_compliance
    
    # Merge with standard summary, inserting after Use of Premises
    if industrial_specific:
        result = {}
        for key, value in summary.items():
            result[key] = value
            if key == "🏢 Use of Premises":
                for industrial_key, industrial_value in industrial_specific.items():
                    result[industrial_key] = industrial_value
    else:
        result = summary
        
    return result


def extract_section_by_keywords(clauses: Dict[str, ClauseExtraction], keywords: List[str], summary_style: SummaryStyle) -> Dict[str, Any]:
    """Extract clauses based on specific keywords"""
    result = {}
    
    for key, clause in clauses.items():
        if any(keyword in key.lower() for keyword in keywords):
            result[key] = {
                "content": clause.content,
                "summary_bullet": clause.summary_bullet,
                "source_excerpt": clause.raw_excerpt,
                "page_number": clause.page_number,
                "page_range": clause.page_range,
                "risk_tags": clause.risk_tags,
                "needs_review": clause.needs_review,
                "field_id": clause.field_id
            }
    
    return result


def extract_overview_section(clauses: Dict[str, ClauseExtraction], summary_style: SummaryStyle) -> Dict[str, Any]:
    """Extract lease overview information with bullet points for relevant data"""
    overview = {}
    
    # Look for relevant clauses
    premises_clauses = {}
    for key, clause in clauses.items():
        if any(term in key.lower() for term in ["landlord", "tenant", "premises", "property", "address", "building", "leased_area", "square_feet", "sqft"]):
            premises_clauses[key] = {
                "content": clause.content,
                "summary_bullet": clause.summary_bullet,
                "source_excerpt": clause.raw_excerpt,
                "page_number": clause.page_number,
                "page_range": clause.page_range,
                "risk_tags": clause.risk_tags,
                "needs_review": clause.needs_review,
                "field_id": clause.field_id,
                "structured_data": clause.structured_data
            }
    
    # If no overview info found
    if not premises_clauses:
        overview["no_overview"] = "No overview information found in the lease document."
        
    return premises_clauses if premises_clauses else overview


def extract_term_section(clauses: Dict[str, ClauseExtraction], summary_style: SummaryStyle) -> Dict[str, Any]:
    """Extract lease term information with bullet points"""
    term_clauses = {}
    
    # Look for relevant clauses
    for key, clause in clauses.items():
        if any(term in key.lower() for term in ["term", "commencement", "expiration", "termination", "renewal", "extension"]):
            term_clauses[key] = {
                "content": clause.content,
                "summary_bullet": clause.summary_bullet,
                "source_excerpt": clause.raw_excerpt,
                "page_number": clause.page_number,
                "page_range": clause.page_range,
                "risk_tags": clause.risk_tags,
                "needs_review": clause.needs_review,
                "field_id": clause.field_id,
                "structured_data": clause.structured_data
            }
    
    # If no term info found
    if not term_clauses:
        term_clauses["no_term"] = "No lease term information found in the lease document."
        
    return term_clauses


def extract_rent_section(clauses: Dict[str, ClauseExtraction], summary_style: SummaryStyle) -> Dict[str, Any]:
    """Extract rent and payment information with detailed breakdown"""
    rent_clauses = {}
    
    # Look for relevant clauses
    for key, clause in clauses.items():
        if any(term in key.lower() for term in ["rent", "payment", "base_rent", "minimum_rent", "security_deposit", "prepaid_rent"]):
            rent_clauses[key] = {
                "content": clause.content,
                "summary_bullet": clause.summary_bullet,
                "source_excerpt": clause.raw_excerpt,
                "page_number": clause.page_number,
                "page_range": clause.page_range,
                "risk_tags": clause.risk_tags,
                "needs_review": clause.needs_review,
                "field_id": clause.field_id,
                "structured_data": clause.structured_data
            }
    
    # If no rent info found
    if not rent_clauses:
        rent_clauses["no_rent"] = "No rent information found in the lease document."
        
    return rent_clauses


def extract_additional_charges_section(clauses: Dict[str, ClauseExtraction], summary_style: SummaryStyle) -> Dict[str, Any]:
    """Extract additional charges information"""
    charges_clauses = {}
    
    # Look for relevant clauses
    for key, clause in clauses.items():
        if any(term in key.lower() for term in ["additional_rent", "cam", "common_area", "maintenance_fee", "operating_expenses", "tax", "insurance", "utilities"]):
            if "maintenance_responsibility" not in key.lower():  # Avoid duplication with maintenance section
                charges_clauses[key] = {
                    "content": clause.content,
                    "summary_bullet": clause.summary_bullet,
                    "source_excerpt": clause.raw_excerpt,
                    "page_number": clause.page_number,
                    "page_range": clause.page_range,
                    "risk_tags": clause.risk_tags,
                    "needs_review": clause.needs_review,
                    "field_id": clause.field_id,
                    "structured_data": clause.structured_data
                }
    
    # If no additional charges info found
    if not charges_clauses:
        charges_clauses["no_charges"] = "No additional charges information found in the lease document."
        
    return charges_clauses


def extract_maintenance_section(clauses: Dict[str, ClauseExtraction], summary_style: SummaryStyle) -> Dict[str, Any]:
    """Extract maintenance responsibilities information"""
    maintenance_clauses = {}
    
    # Look for relevant clauses
    for key, clause in clauses.items():
        if any(term in key.lower() for term in ["maintenance", "repair", "alteration", "improvement"]):
            maintenance_clauses[key] = {
                "content": clause.content,
                "summary_bullet": clause.summary_bullet,
                "source_excerpt": clause.raw_excerpt,
                "page_number": clause.page_number,
                "page_range": clause.page_range,
                "risk_tags": clause.risk_tags,
                "needs_review": clause.needs_review,
                "field_id": clause.field_id,
                "structured_data": clause.structured_data
            }
    
    # If no maintenance info found
    if not maintenance_clauses:
        maintenance_clauses["no_maintenance"] = "No maintenance responsibilities information found in the lease document."
        
    return maintenance_clauses


def extract_use_section(clauses: Dict[str, ClauseExtraction], summary_style: SummaryStyle) -> Dict[str, Any]:
    """Extract use of premises information"""
    use_clauses = {}
    
    # Look for relevant clauses
    for key, clause in clauses.items():
        if any(term in key.lower() for term in ["use", "permitted_use", "prohibited_use", "exclusive"]):
            use_clauses[key] = {
                "content": clause.content,
                "summary_bullet": clause.summary_bullet,
                "source_excerpt": clause.raw_excerpt,
                "page_number": clause.page_number,
                "page_range": clause.page_range,
                "risk_tags": clause.risk_tags,
                "needs_review": clause.needs_review,
                "field_id": clause.field_id,
                "structured_data": clause.structured_data
            }
    
    # If no use info found
    if not use_clauses:
        use_clauses["no_use"] = "No use of premises information found in the lease document."
        
    return use_clauses


def extract_assignment_section(clauses: Dict[str, ClauseExtraction], summary_style: SummaryStyle) -> Dict[str, Any]:
    """Extract assignment and subletting information"""
    assignment_clauses = {}
    
    # Look for relevant clauses
    for key, clause in clauses.items():
        if any(term in key.lower() for term in ["assignment", "sublet", "transfer", "subletting"]):
            assignment_clauses[key] = {
                "content": clause.content,
                "summary_bullet": clause.summary_bullet,
                "source_excerpt": clause.raw_excerpt,
                "page_number": clause.page_number,
                "page_range": clause.page_range,
                "risk_tags": clause.risk_tags,
                "needs_review": clause.needs_review,
                "field_id": clause.field_id,
                "structured_data": clause.structured_data
            }
    
    # If no assignment info found
    if not assignment_clauses:
        assignment_clauses["no_assignment"] = "No assignment and subletting information found in the lease document."
        
    return assignment_clauses


def extract_insurance_section(clauses: Dict[str, ClauseExtraction], summary_style: SummaryStyle) -> Dict[str, Any]:
    """Extract insurance requirements information"""
    insurance_clauses = {}
    
    # Look for relevant clauses
    for key, clause in clauses.items():
        if any(term in key.lower() for term in ["insurance", "liability", "property_insurance", "waiver", "indemnity", "indemnification"]):
            insurance_clauses[key] = {
                "content": clause.content,
                "summary_bullet": clause.summary_bullet,
                "source_excerpt": clause.raw_excerpt,
                "page_number": clause.page_number,
                "page_range": clause.page_range,
                "risk_tags": clause.risk_tags,
                "needs_review": clause.needs_review,
                "field_id": clause.field_id,
                "structured_data": clause.structured_data
            }
    
    # If no insurance info found
    if not insurance_clauses:
        insurance_clauses["no_insurance"] = "No insurance requirements information found in the lease document."
        
    return insurance_clauses


def extract_casualty_section(clauses: Dict[str, ClauseExtraction], summary_style: SummaryStyle) -> Dict[str, Any]:
    """Extract casualty information"""
    casualty_clauses = {}
    
    # Look for relevant clauses
    for key, clause in clauses.items():
        if any(term in key.lower() for term in ["casualty", "damage", "destruction", "fire", "rebuild", "restoration"]):
            casualty_clauses[key] = {
                "content": clause.content,
                "summary_bullet": clause.summary_bullet,
                "source_excerpt": clause.raw_excerpt,
                "page_number": clause.page_number,
                "page_range": clause.page_range,
                "risk_tags": clause.risk_tags,
                "needs_review": clause.needs_review,
                "field_id": clause.field_id,
                "structured_data": clause.structured_data
            }
    
    # If no casualty info found
    if not casualty_clauses:
        casualty_clauses["no_casualty"] = "No casualty information found in the lease document."
        
    return casualty_clauses


def extract_eminent_domain_section(clauses: Dict[str, ClauseExtraction], summary_style: SummaryStyle) -> Dict[str, Any]:
    """Extract eminent domain information"""
    eminent_domain_clauses = {}
    
    # Look for relevant clauses
    for key, clause in clauses.items():
        if any(term in key.lower() for term in ["eminent_domain", "condemnation", "taking", "condemn"]):
            eminent_domain_clauses[key] = {
                "content": clause.content,
                "summary_bullet": clause.summary_bullet,
                "source_excerpt": clause.raw_excerpt,
                "page_number": clause.page_number,
                "page_range": clause.page_range,
                "risk_tags": clause.risk_tags,
                "needs_review": clause.needs_review,
                "field_id": clause.field_id,
                "structured_data": clause.structured_data
            }
    
    # If no eminent domain info found
    if not eminent_domain_clauses:
        eminent_domain_clauses["no_eminent_domain"] = "No eminent domain information found in the lease document."
        
    return eminent_domain_clauses


def extract_legal_section(clauses: Dict[str, ClauseExtraction], summary_style: SummaryStyle) -> Dict[str, Any]:
    """Extract legal clauses information"""
    legal_clauses = {}
    
    # Look for relevant clauses
    for key, clause in clauses.items():
        if any(term in key.lower() for term in ["default", "remed", "attorney", "dispute", "arbitration", "mediation", "law", "jurisdiction", "notice"]):
            legal_clauses[key] = {
                "content": clause.content,
                "summary_bullet": clause.summary_bullet,
                "source_excerpt": clause.raw_excerpt,
                "page_number": clause.page_number,
                "page_range": clause.page_range,
                "risk_tags": clause.risk_tags,
                "needs_review": clause.needs_review,
                "field_id": clause.field_id,
                "structured_data": clause.structured_data
            }
    
    # If no legal info found
    if not legal_clauses:
        legal_clauses["no_legal"] = "No legal clauses information found in the lease document."
        
    return legal_clauses


def extract_entry_section(clauses: Dict[str, ClauseExtraction], summary_style: SummaryStyle) -> Dict[str, Any]:
    """Extract entry and access information"""
    entry_clauses = {}
    
    # Look for relevant clauses
    for key, clause in clauses.items():
        if any(term in key.lower() for term in ["entry", "access", "inspect", "showing", "landlord_entry"]):
            entry_clauses[key] = {
                "content": clause.content,
                "summary_bullet": clause.summary_bullet,
                "source_excerpt": clause.raw_excerpt,
                "page_number": clause.page_number,
                "page_range": clause.page_range,
                "risk_tags": clause.risk_tags,
                "needs_review": clause.needs_review,
                "field_id": clause.field_id,
                "structured_data": clause.structured_data
            }
    
    # If no entry info found
    if not entry_clauses:
        entry_clauses["no_entry"] = "No entry and access information found in the lease document."
        
    return entry_clauses


def extract_miscellaneous_section(clauses: Dict[str, ClauseExtraction], summary_style: SummaryStyle) -> Dict[str, Any]:
    """Extract miscellaneous information"""
    misc_clauses = {}
    
    # Look for relevant clauses
    for key, clause in clauses.items():
        if any(term in key.lower() for term in ["option", "right_of_first", "rofr", "rofo", "expansion", "relocation", "holdover", "quiet_enjoyment", "estoppel", "subordination", "snda", "signage", "parking"]):
            misc_clauses[key] = {
                "content": clause.content,
                "summary_bullet": clause.summary_bullet,
                "source_excerpt": clause.raw_excerpt,
                "page_number": clause.page_number,
                "page_range": clause.page_range,
                "risk_tags": clause.risk_tags,
                "needs_review": clause.needs_review,
                "field_id": clause.field_id,
                "structured_data": clause.structured_data
            }
    
    # If no miscellaneous info found
    if not misc_clauses:
        misc_clauses["no_misc"] = "No miscellaneous information found in the lease document."
        
    return misc_clauses


def extract_risk_section(clauses: Dict[str, ClauseExtraction]) -> str:
    """Extract risk flags from all clauses and format as markdown"""
    risk_flags = []
    
    # Look for risk tags in all clauses
    for key, clause in clauses.items():
        if clause.risk_tags:
            for risk in clause.risk_tags:
                risk_flags.append({
                    "clause": key.replace("_", " ").title(),
                    "level": risk.get("level", "unknown"),
                    "description": risk.get("description", "No risk description provided"),
                    "page_number": clause.page_number
                })
    
    # Format risk flags as markdown
    if risk_flags:
        markdown = ""
        
        # Group risks by severity
        high_risks = [r for r in risk_flags if r["level"] == "high"]
        medium_risks = [r for r in risk_flags if r["level"] == "medium"]
        low_risks = [r for r in risk_flags if r["level"] == "low"]
        
        # Add high risks
        if high_risks:
            markdown += "### High Severity Risks\n\n"
            for risk in high_risks:
                page_info = f" (Page {risk['page_number']})" if risk['page_number'] else ""
                markdown += f"🔴 **{risk['clause']}{page_info}**: {risk['description']}\n\n"
                
        # Add medium risks
        if medium_risks:
            markdown += "### Medium Severity Risks\n\n"
            for risk in medium_risks:
                page_info = f" (Page {risk['page_number']})" if risk['page_number'] else ""
                markdown += f"🟠 **{risk['clause']}{page_info}**: {risk['description']}\n\n"
                
        # Add low risks
        if low_risks:
            markdown += "### Low Severity Risks\n\n"
            for risk in low_risks:
                page_info = f" (Page {risk['page_number']})" if risk['page_number'] else ""
                markdown += f"🟡 **{risk['clause']}{page_info}**: {risk['description']}\n\n"
                
        return markdown
    else:
        return "No significant risks identified in the lease document."


def extract_missing_clauses(clauses: Dict[str, ClauseExtraction]) -> str:
    """Identify missing or incomplete clauses"""
    # Define essential clauses that should be in every lease
    essential_clauses = {
        "premises": ["premises", "leased_premises", "demised_premises"],
        "lease_term": ["term", "commencement", "expiration"],
        "rent": ["rent", "payment", "base_rent"],
        "maintenance": ["maintenance", "repair"],
        "use_of_premises": ["use", "permitted_use"],
        "assignment": ["assignment", "sublet", "transfer"],
        "insurance": ["insurance", "liability"],
        "default": ["default", "remedies"]
    }
    
    # Check for missing clauses
    missing = []
    for category, keywords in essential_clauses.items():
        found = False
        for key in clauses.keys():
            if any(keyword in key.lower() for keyword in keywords):
                found = True
                break
        if not found:
            missing.append(category.replace("_", " ").title())
    
    # Check for incomplete or low-confidence clauses
    incomplete = []
    for key, clause in clauses.items():
        if clause.needs_review or (clause.confidence and clause.confidence < 0.7):
            incomplete.append({
                "clause": key.replace("_", " ").title(),
                "confidence": clause.confidence if clause.confidence else 0.5,
                "page_number": clause.page_number
            })
    
    # Format as markdown
    markdown = ""
    
    # Missing clauses
    if missing:
        markdown += "### Missing Clauses\n\n"
        for clause in missing:
            markdown += f"❗ **{clause}** - Not found in the lease document\n\n"
    
    # Incomplete clauses
    if incomplete:
        markdown += "### Clauses Needing Review\n\n"
        for clause_info in incomplete:
            page_info = f" (Page {clause_info['page_number']})" if clause_info['page_number'] else ""
            confidence = int(clause_info['confidence'] * 100)
            markdown += f"⚠️ **{clause_info['clause']}{page_info}** - Low confidence detection ({confidence}%)\n\n"
    
    if not missing and not incomplete:
        markdown = "No essential clauses appear to be missing from the lease document."
    
    return markdown


def format_executive_style(summary: Dict[str, Any]) -> Dict[str, Any]:
    """Format the summary in executive style (more concise)"""
    # This is a more sophisticated implementation that actually condenses the content
    executive_summary = {}
    
    for section_title, section_content in summary.items():
        if isinstance(section_content, dict):
            condensed_section = {}
            
            for key, clause_data in section_content.items():
                if isinstance(clause_data, dict):
                    # Use summary bullet instead of full content if available
                    if clause_data.get('summary_bullet'):
                        clause_data['content'] = clause_data['summary_bullet']
                    
                    # Keep only high and medium risk tags
                    if clause_data.get('risk_tags'):
                        clause_data['risk_tags'] = [risk for risk in clause_data['risk_tags'] 
                                                   if risk.get('level') in ['high', 'medium']]
                    
                    # Remove detailed source excerpts if they're long
                    if clause_data.get('source_excerpt') and len(clause_data.get('source_excerpt')) > 100:
                        clause_data['source_excerpt'] = clause_data['source_excerpt'][:100] + "..."
                        
                    condensed_section[key] = clause_data
                else:
                    condensed_section[key] = clause_data
                    
            executive_summary[section_title] = condensed_section
        else:
            executive_summary[section_title] = section_content
    
    return executive_summary
