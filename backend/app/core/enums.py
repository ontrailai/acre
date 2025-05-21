from enum import Enum, auto
from typing import List, Dict, Optional

class ClauseCategory(Enum):
    PREMISES = "premises"
    TERM = "term"
    RENT = "rent"
    MAINTENANCE = "maintenance"
    USE = "use"
    ASSIGNMENT = "assignment"
    INSURANCE = "insurance"
    DEFAULT = "default"
    OPERATING_HOURS = "operating_hours"
    COMMON_AREA = "common_area"
    PERCENTAGE_RENT = "percentage_rent"
    BUILDING_SERVICES = "building_services"
    OPERATING_EXPENSES = "operating_expenses"
    TENANT_IMPROVEMENTS = "tenant_improvements"
    ENVIRONMENTAL = "environmental"
    HAZARDOUS_MATERIALS = "hazardous_materials"
    SIGNAGE = "signage"
    QUIET_ENJOYMENT = "quiet_enjoyment"
    NOTICES = "notices"
    PARKING = "parking"
    TERMINATION = "termination"
    CO_TENANCY = "co_tenancy"
    UTILITIES = "utilities"
    CASUALTY = "casualty"
    ENTRY = "entry"
    
    def display_name(self) -> str:
        """Return a human-readable display name for the clause category"""
        return self.value.replace("_", " ").title()
    
    def aliases(self) -> List[str]:
        """
        Returns a list of common keyword aliases for each clause type.
        These aliases are used to detect clause category from varied raw names or text.
        """
        aliases_map: Dict[ClauseCategory, List[str]] = {
            ClauseCategory.PREMISES: ["premises", "leased premises", "demised premises"],
            ClauseCategory.TERM: ["term", "commencement", "expiration", "lease term"],
            ClauseCategory.RENT: ["rent", "payment", "base rent", "minimum rent"],
            ClauseCategory.MAINTENANCE: ["maintenance", "repair", "alteration"],
            ClauseCategory.USE: ["use", "permitted use", "prohibited use"],
            ClauseCategory.ASSIGNMENT: ["assignment", "sublet", "transfer", "subletting"],
            ClauseCategory.INSURANCE: ["insurance", "liability", "indemnity", "indemnification"],
            ClauseCategory.DEFAULT: ["default", "remedies", "events of default"],
            ClauseCategory.OPERATING_HOURS: ["operating hours", "business hours", "hours of operation"],
            ClauseCategory.COMMON_AREA: ["cam", "common area", "common area maintenance", "opex"],
            ClauseCategory.PERCENTAGE_RENT: ["percentage rent", "overage rent"],
            ClauseCategory.BUILDING_SERVICES: ["building services", "services"],
            ClauseCategory.OPERATING_EXPENSES: ["operating expenses", "opex", "expenses"],
            ClauseCategory.TENANT_IMPROVEMENTS: ["tenant improvements", "improvements", "allowance", "buildout"],
            ClauseCategory.ENVIRONMENTAL: ["environmental", "compliance", "environmental compliance"],
            ClauseCategory.HAZARDOUS_MATERIALS: ["hazardous", "hazmat", "hazardous materials"],
            ClauseCategory.SIGNAGE: ["signage", "sign rights", "sign restrictions"],
            ClauseCategory.QUIET_ENJOYMENT: ["quiet enjoyment", "peaceful possession"],
            ClauseCategory.NOTICES: ["notices", "notice", "notice provisions"],
            ClauseCategory.PARKING: ["parking", "reserved parking"],
            ClauseCategory.TERMINATION: ["termination", "early termination", "break clause"],
            ClauseCategory.CO_TENANCY: ["co-tenancy", "cotenancy", "anchor tenant"],
            ClauseCategory.UTILITIES: ["utilities", "electric", "water", "gas"],
            ClauseCategory.CASUALTY: ["casualty", "damage", "destruction"],
            ClauseCategory.ENTRY: ["entry", "landlord entry", "inspection"]
        }
        return aliases_map.get(self, [])
    
    @classmethod
    def match_from_string(cls, text: str) -> Optional["ClauseCategory"]:
        """
        Match an arbitrary input string to the most appropriate clause category
        using the aliases.
        
        Args:
            text: The input string to match
            
        Returns:
            The matching ClauseCategory or None if no match found
        """
        normalized = text.lower()
        
        # First, try direct enum value match
        try:
            normalized_enum = normalized.replace(" ", "_")
            return cls(normalized_enum)
        except ValueError:
            pass
            
        # Then try to match against aliases
        for category in cls:
            if any(alias in normalized for alias in category.aliases()):
                return category
                
        # No match found
        return None
