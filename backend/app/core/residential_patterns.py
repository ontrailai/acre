"""
Enhanced pattern matching for residential leases

This module adds improved pattern matching that better handles residential lease formats
which differ from commercial leases in terminology and structure.
"""

import re
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


def extract_residential_lease_patterns(full_text: str) -> Dict[str, Any]:
    """
    Enhanced pattern matching specifically for residential leases.
    Returns a dictionary of extracted lease terms.
    """
    extracted_data = {}
    
    # Handle multiple tenant names in residential leases
    # Pattern: "Deborah Hample and Riley Pasha (together and separately, Tenant)"
    multi_tenant_pattern = r"([A-Za-z\s]+?)\s+and\s+([A-Za-z\s]+?)\s*\((?:together\s+and\s+separately,?\s*)?Tenant\)"
    multi_tenant_match = re.search(multi_tenant_pattern, full_text, re.IGNORECASE)
    
    if multi_tenant_match:
        tenant1 = multi_tenant_match.group(1).strip()
        tenant2 = multi_tenant_match.group(2).strip()
        extracted_data['tenant'] = f"{tenant1} and {tenant2}"
        logger.debug(f"Found multiple tenants: {extracted_data['tenant']}")
    else:
        # Try single tenant patterns
        tenant_patterns = [
            r"(?:Tenant|TENANT|Lessee|LESSEE)[:\s]*([A-Za-z\s\.,&'-]+?)(?:\n|,|\()",
            r"([A-Za-z\s\.,&'-]+?)\s*\((?:\"?Tenant\"?|\"?Lessee\"?)\)",
            r"and\s+([A-Za-z\s\.,&'-]+?)\s*\((?:hereinafter.*?)?Tenant\)"
        ]
        
        for pattern in tenant_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                extracted_data['tenant'] = match.group(1).strip()
                logger.debug(f"Found tenant: {extracted_data['tenant']}")
                break
    
    # Enhanced landlord patterns for residential format
    landlord_patterns = [
        r"([A-Za-z\s\.,&'-]+?)\s*\((?:\"?Landlord\"?|\"?Lessor\"?)\)",
        r"between\s+([A-Za-z\s\.,&'-]+?)\s*\(Landlord\)",
        r"(?:Landlord|LANDLORD|Lessor|Owner)[:\s]*([A-Za-z\s\.,&'-]+?)(?:\n|,|\()",
        r"This\s+(?:Residential\s+)?Lease.*?between\s+([A-Za-z\s\.,&'-]+?)\s*\(Landlord\)"
    ]
    
    for pattern in landlord_patterns:
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            extracted_data['landlord'] = match.group(1).strip()
            logger.debug(f"Found landlord: {extracted_data['landlord']}")
            break
    
    # Property address - handle residential format
    # Pattern: "1818 McKee St San Diego, CA 92110" or variations
    address_patterns = [
        r"(?:for|Property)[:\s]*(\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Way|Boulevard|Blvd)[^,]*,\s*[A-Za-z\s]+,\s*[A-Z]{2}\s*\d{5})",
        r"(?:Property Location|Located at)[:\s]*([^\n]+)",
        r"(\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr)[^,\n]*,\s*[A-Za-z\s]+,\s*[A-Z]{2}\s*\d{5})"
    ]
    
    for pattern in address_patterns:
        match = re.search(pattern, full_text, re.IGNORECASE | re.MULTILINE)
        if match:
            extracted_data['address'] = match.group(1).strip()
            logger.debug(f"Found address: {extracted_data['address']}")
            break
    
    # Term dates - residential lease format
    # Pattern: "will begin on January 31, 2025 (Start Date) and end on January 31, 2026"
    term_pattern = r"(?:will\s+)?begin\s+on\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})\s*(?:\(Start\s+Date\))?\s*and\s+end\s+on\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})"
    term_match = re.search(term_pattern, full_text, re.IGNORECASE)
    
    if term_match:
        extracted_data['commencement_date'] = term_match.group(1)
        extracted_data['expiration_date'] = term_match.group(2)
        logger.debug(f"Found term dates: {extracted_data['commencement_date']} to {extracted_data['expiration_date']}")
    else:
        # Try alternative patterns
        start_patterns = [
            r"(?:Start Date|Commencement Date)[:\s]*([A-Za-z]+\s+\d{1,2},\s+\d{4})",
            r"commenc\w+\s+on\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})"
        ]
        
        for pattern in start_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                extracted_data['commencement_date'] = match.group(1)
                break
                
        end_patterns = [
            r"(?:Expiration Date|End Date)[:\s]*([A-Za-z]+\s+\d{1,2},\s+\d{4})",
            r"end\w*\s+on\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})"
        ]
        
        for pattern in end_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                extracted_data['expiration_date'] = match.group(1)
                break
    
    # Monthly rent - residential format
    # Pattern: "The Monthly Rent is $3,650.00"
    rent_patterns = [
        r"(?:The\s+)?Monthly\s+Rent\s+is\s+\$\s*([\d,]+(?:\.\d{2})?)",
        r"monthly\s+rent.*?\$\s*([\d,]+(?:\.\d{2})?)",
        r"Base\s+Rent.*?\$\s*([\d,]+(?:\.\d{2})?)\s*(?:per\s+month|monthly)?",
        r"\$\s*([\d,]+(?:\.\d{2})?)\s*(?:per\s+month|/month|monthly)"
    ]
    
    for pattern in rent_patterns:
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            extracted_data['monthly_rent'] = f"${match.group(1)}"
            logger.debug(f"Found monthly rent: {extracted_data['monthly_rent']}")
            break
    
    # Security deposit - residential format
    # Pattern: "The security deposit is $4,650.00"
    deposit_patterns = [
        r"(?:The\s+)?[Ss]ecurity\s+[Dd]eposit\s+is\s+\$\s*([\d,]+(?:\.\d{2})?)",
        r"\$\s*([\d,]+(?:\.\d{2})?)\s+Security\s+Deposit",
        r"Security\s+Deposit[:\s]*\$\s*([\d,]+(?:\.\d{2})?)"
    ]
    
    for pattern in deposit_patterns:
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            extracted_data['security_deposit'] = f"${match.group(1)}"
            logger.debug(f"Found security deposit: {extracted_data['security_deposit']}")
            break
    
    # Permitted use for residential leases
    # Usually "residential purposes only" or similar
    use_patterns = [
        r"(?:use.*?for|used\s+for|residential\s+purposes)\s+([^\.]+)(?:only)?",
        r"(?:Property.*?used|occupy.*?for)\s+([^\.]+)"
    ]
    
    for pattern in use_patterns:
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            use_text = match.group(1).strip()
            if 'residential' in use_text.lower():
                extracted_data['permitted_use'] = use_text
                break
    
    # If no specific use found but it's clearly residential
    if 'permitted_use' not in extracted_data and 'residential lease' in full_text.lower():
        extracted_data['permitted_use'] = "residential purposes only"
    
    return extracted_data


def merge_extraction_results(pattern_results: Dict[str, Any], existing_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge pattern extraction results with existing results, preferring non-null values.
    """
    merged = existing_results.copy()
    
    for key, value in pattern_results.items():
        if value and (key not in merged or not merged[key]):
            merged[key] = value
            
    return merged
