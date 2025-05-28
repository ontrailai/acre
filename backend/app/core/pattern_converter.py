def _convert_extracted_data_to_clauses(data: Dict[str, Any]) -> Dict[str, ClauseExtraction]:
    """Convert extracted pattern data to clause format"""
    from app.schemas import ClauseExtraction
    import json
    
    clauses = {}
    
    # Group by category
    party_data = {}
    premises_data = {}
    term_data = {}
    rent_data = {}
    
    # Sort data into categories
    for key, value in data.items():
        if key in ['landlord', 'tenant']:
            party_data[f"{key}_name"] = value
        elif key in ['address', 'square_feet', 'suite']:
            premises_data[key] = value
        elif key in ['commencement_date', 'expiration_date', 'term_length']:
            term_data[key] = value
        elif key in ['monthly_rent', 'annual_rent']:
            rent_data['base_rent' if key == 'monthly_rent' else key] = value
        elif key == 'security_deposit':
            clauses["security_deposit_data"] = ClauseExtraction(
                content=json.dumps({"amount": value}, indent=2),
                raw_excerpt="Extracted security deposit",
                confidence=0.85,
                page_number=1,
                risk_tags=[],
                summary_bullet=f"Security Deposit: {value}",
                structured_data={"amount": value},
                needs_review=False,
                field_id="security_deposit"
            )
        elif key == 'permitted_use':
            clauses["use_data"] = ClauseExtraction(
                content=json.dumps({"permitted_use": value}, indent=2),
                raw_excerpt="Extracted permitted use",
                confidence=0.85,
                page_number=1,
                risk_tags=[],
                summary_bullet=f"Permitted Use: {value}",
                structured_data={"permitted_use": value},
                needs_review=False,
                field_id="use"
            )
    
    # Create clauses for grouped data
    if party_data:
        clauses["parties_data"] = ClauseExtraction(
            content=json.dumps(party_data, indent=2),
            raw_excerpt="Extracted party information",
            confidence=0.85,
            page_number=1,
            risk_tags=[],
            summary_bullet=f"Landlord: {party_data.get('landlord_name', 'Unknown')} | Tenant: {party_data.get('tenant_name', 'Unknown')}",
            structured_data=party_data,
            needs_review=False,
            field_id="parties"
        )
        
    if premises_data:
        clauses["premises_data"] = ClauseExtraction(
            content=json.dumps(premises_data, indent=2),
            raw_excerpt="Extracted premises information",
            confidence=0.85,
            page_number=1,
            risk_tags=[],
            summary_bullet=f"Property: {premises_data.get('address', 'Unknown')}",
            structured_data=premises_data,
            needs_review=False,
            field_id="premises"
        )
        
    if term_data:
        clauses["term_data"] = ClauseExtraction(
            content=json.dumps(term_data, indent=2),
            raw_excerpt="Extracted term information",
            confidence=0.85,
            page_number=1,
            risk_tags=[],
            summary_bullet=f"Term: {term_data.get('commencement_date', 'TBD')} to {term_data.get('expiration_date', 'TBD')}",
            structured_data=term_data,
            needs_review=False,
            field_id="term"
        )
        
    if rent_data:
        clauses["rent_data"] = ClauseExtraction(
            content=json.dumps(rent_data, indent=2),
            raw_excerpt="Extracted rent information",
            confidence=0.85,
            page_number=1,
            risk_tags=[],
            summary_bullet=f"Base Rent: {rent_data.get('base_rent', 'Unknown')}",
            structured_data=rent_data,
            needs_review=False,
            field_id="rent"
        )
    
    return clauses
