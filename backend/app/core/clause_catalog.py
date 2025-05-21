from typing import Dict, List, Set
from app.schemas import LeaseType
from app.utils.risk_analysis.enums import ClauseCategory
from app.utils.logger import logger

def get_essential_clauses(lease_type: LeaseType) -> Dict[str, List[str]]:
    """
    Returns a dictionary of essential clauses based on lease type.
    
    Args:
        lease_type: Type of lease (RETAIL, OFFICE, INDUSTRIAL)
        
    Returns:
        Dictionary with clause categories as keys and lists of relevant keywords as values
    """
    # Define base clauses common to all lease types
    base_clauses = {
        ClauseCategory.PREMISES.value: ["premises", "leased_premises", "demised_premises"],
        ClauseCategory.TERM.value: ["term", "commencement", "expiration", "lease_term"],
        ClauseCategory.RENT.value: ["rent", "payment", "base_rent", "minimum_rent"],
        ClauseCategory.MAINTENANCE.value: ["maintenance", "repair", "alteration"],
        ClauseCategory.USE.value: ["use", "permitted_use", "prohibited_use"],
        ClauseCategory.ASSIGNMENT.value: ["assignment", "sublet", "transfer", "subletting"],
        ClauseCategory.INSURANCE.value: ["insurance", "liability", "indemnity", "indemnification"],
        ClauseCategory.DEFAULT.value: ["default", "remedies", "events_of_default"]
    }
    
    # Create a copy of the base clauses to avoid modifying the original
    essential_clauses = base_clauses.copy()
    
    # Add lease-type specific essential clauses
    if lease_type == LeaseType.RETAIL:
        essential_clauses.update({
            ClauseCategory.OPERATING_HOURS.value: ["operating_hours", "hours_of_operation", "business_hours"],
            ClauseCategory.COMMON_AREA.value: ["cam", "common_area", "common_area_maintenance", "operating_expenses"],
            ClauseCategory.PERCENTAGE_RENT.value: ["percentage_rent", "overage_rent"]
        })
    elif lease_type == LeaseType.OFFICE:
        essential_clauses.update({
            ClauseCategory.BUILDING_SERVICES.value: ["building_services", "services"],
            ClauseCategory.OPERATING_EXPENSES.value: ["operating_expenses", "opex", "expenses"],
            ClauseCategory.TENANT_IMPROVEMENTS.value: ["improvements", "tenant_improvements", "allowance"]
        })
    elif lease_type == LeaseType.INDUSTRIAL:
        essential_clauses.update({
            ClauseCategory.ENVIRONMENTAL.value: ["environmental", "compliance", "environmental_compliance"],
            ClauseCategory.HAZARDOUS_MATERIALS.value: ["hazardous", "hazmat", "hazardous_materials"]
        })
    
    # Check for missing clause categories and log warnings
    all_categories = {category.value for category in ClauseCategory}
    included_categories = set(essential_clauses.keys())
    missing_categories = all_categories - included_categories
    
    if missing_categories:
        logger.warning(
            f"Missing clause categories in {lease_type.name} configuration: {', '.join(missing_categories)}"
        )
    
    return essential_clauses


def get_clause_categories_by_lease_type(lease_type: LeaseType) -> List[ClauseCategory]:
    """
    Returns a list of clause categories that are relevant for a specific lease type.
    
    Args:
        lease_type: Type of lease (RETAIL, OFFICE, INDUSTRIAL)
        
    Returns:
        List of ClauseCategory enum members relevant to the specified lease type
    """
    # Common categories for all lease types
    common_categories = [
        ClauseCategory.PREMISES,
        ClauseCategory.TERM,
        ClauseCategory.RENT,
        ClauseCategory.MAINTENANCE,
        ClauseCategory.USE,
        ClauseCategory.ASSIGNMENT,
        ClauseCategory.INSURANCE, 
        ClauseCategory.DEFAULT,
        ClauseCategory.CASUALTY,
        ClauseCategory.NOTICES,
        ClauseCategory.UTILITIES,
        ClauseCategory.QUIET_ENJOYMENT,
        ClauseCategory.ENTRY
    ]
    
    # Lease type specific categories
    if lease_type == LeaseType.RETAIL:
        return common_categories + [
            ClauseCategory.OPERATING_HOURS,
            ClauseCategory.COMMON_AREA,
            ClauseCategory.PERCENTAGE_RENT,
            ClauseCategory.CO_TENANCY,
            ClauseCategory.SIGNAGE
        ]
    elif lease_type == LeaseType.OFFICE:
        return common_categories + [
            ClauseCategory.BUILDING_SERVICES,
            ClauseCategory.OPERATING_EXPENSES,
            ClauseCategory.TENANT_IMPROVEMENTS,
            ClauseCategory.PARKING
        ]
    elif lease_type == LeaseType.INDUSTRIAL:
        return common_categories + [
            ClauseCategory.ENVIRONMENTAL,
            ClauseCategory.HAZARDOUS_MATERIALS,
            ClauseCategory.PARKING,
            ClauseCategory.SIGNAGE
        ]
    
    # Return common categories as fallback
    return common_categories


def is_high_risk_clause(category: ClauseCategory) -> bool:
    """
    Determines whether a clause category is considered high risk for lease analysis.
    
    Args:
        category: The clause category to check
        
    Returns:
        True if the clause is considered high risk, False otherwise
    """
    high_risk_categories = [
        ClauseCategory.TERMINATION,
        ClauseCategory.ASSIGNMENT,
        ClauseCategory.CO_TENANCY,
        ClauseCategory.ENVIRONMENTAL,
        ClauseCategory.HAZARDOUS_MATERIALS
    ]
    
    return category in high_risk_categories


def is_medium_risk_clause(category: ClauseCategory) -> bool:
    """
    Determines whether a clause category is considered medium risk for lease analysis.
    
    Args:
        category: The clause category to check
        
    Returns:
        True if the clause is considered medium risk, False otherwise
    """
    medium_risk_categories = [
        ClauseCategory.USE,
        ClauseCategory.MAINTENANCE,
        ClauseCategory.INSURANCE,
        ClauseCategory.OPERATING_EXPENSES,
        ClauseCategory.PERCENTAGE_RENT
    ]
    
    return category in medium_risk_categories
