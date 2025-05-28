"""
Consistency Checker and Validation System

This module provides comprehensive validation and consistency checking for
extracted lease data across multiple documents and amendments.
"""

from typing import Dict, List, Optional, Any, Tuple, Set
from datetime import datetime, date
from dataclasses import dataclass, field
import re
from decimal import Decimal
from app.utils.logger import logger


@dataclass
class ValidationIssue:
    """Represents a validation issue found"""
    issue_type: str
    severity: str  # 'high', 'medium', 'low'
    description: str
    location: str  # Where in the document(s)
    expected_value: Any = None
    actual_value: Any = None
    suggestion: Optional[str] = None


@dataclass 
class ConsistencyReport:
    """Complete consistency check report"""
    issues: List[ValidationIssue]
    warnings: List[str]
    cross_references_validated: int
    calculations_validated: int
    dates_validated: int
    terms_validated: int
    overall_score: float  # 0-100
    

class ConsistencyChecker:
    """
    Main consistency checking class that validates extracted data
    """
    
    def __init__(self):
        self.high_stakes_clauses = [
            'default', 'termination', 'indemnification', 'liability',
            'insurance', 'guaranty', 'assignment', 'subletting'
        ]
        self.calculation_tolerance = 0.01  # 1% tolerance for calculations
        
    def validate_extraction(self, extracted_data: Dict[str, Any], 
                          document_graph=None) -> ConsistencyReport:
        """
        Comprehensive validation of extracted data
        """
        issues = []
        warnings = []
        
        # Run various validation checks
        issues.extend(self._validate_dates(extracted_data))
        issues.extend(self._validate_financial_calculations(extracted_data))
        issues.extend(self._validate_cross_references(extracted_data))
        issues.extend(self._validate_defined_terms(extracted_data))
        issues.extend(self._validate_high_stakes_clauses(extracted_data))
        
        # If we have a document graph, validate across documents
        if document_graph:
            issues.extend(self._validate_amendments(extracted_data, document_graph))
            issues.extend(self._validate_cross_document_references(extracted_data, document_graph))
            
        # Calculate metrics
        total_validations = (
            len(self._get_all_dates(extracted_data)) +
            len(self._get_all_calculations(extracted_data)) +
            len(self._get_all_references(extracted_data)) +
            len(self._get_all_defined_terms(extracted_data))
        )
        
        # Calculate score (100 - percentage of issues)
        issue_percentage = (len(issues) / total_validations * 100) if total_validations > 0 else 0
        overall_score = max(0, 100 - issue_percentage)
        
        return ConsistencyReport(
            issues=issues,
            warnings=warnings,
            cross_references_validated=len(self._get_all_references(extracted_data)),
            calculations_validated=len(self._get_all_calculations(extracted_data)),
            dates_validated=len(self._get_all_dates(extracted_data)),
            terms_validated=len(self._get_all_defined_terms(extracted_data)),
            overall_score=overall_score
        )
        
    def _validate_dates(self, data: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate date consistency"""
        issues = []
        dates = self._get_all_dates(data)
        
        # Check for logical consistency
        if 'lease_commencement' in dates and 'lease_expiration' in dates:
            commence = self._parse_date(dates['lease_commencement'])
            expire = self._parse_date(dates['lease_expiration'])
            
            if commence and expire and commence >= expire:
                issues.append(ValidationIssue(
                    issue_type="date_logic_error",
                    severity="high",
                    description="Lease commencement date is after or equal to expiration date",
                    location="Term section",
                    expected_value="Commencement < Expiration",
                    actual_value=f"Commencement: {commence}, Expiration: {expire}",
                    suggestion="Verify lease term dates are correct"
                ))
                
        # Check rent commencement vs lease commencement
        if 'rent_commencement' in dates and 'lease_commencement' in dates:
            rent_commence = self._parse_date(dates['rent_commencement'])
            lease_commence = self._parse_date(dates['lease_commencement'])
            
            if rent_commence and lease_commence and rent_commence < lease_commence:
                issues.append(ValidationIssue(
                    issue_type="date_sequence_error",
                    severity="medium",
                    description="Rent commencement before lease commencement",
                    location="Term section",
                    expected_value="Rent starts on or after lease commencement",
                    actual_value=f"Rent: {rent_commence}, Lease: {lease_commence}",
                    suggestion="Verify if there's a separate rent commencement provision"
                ))
                
        # Check option exercise deadlines
        for key, value in dates.items():
            if 'option' in key and 'deadline' in key:
                deadline = self._parse_date(value)
                if deadline and 'lease_expiration' in dates:
                    expire = self._parse_date(dates['lease_expiration'])
                    if expire and deadline > expire:
                        issues.append(ValidationIssue(
                            issue_type="option_deadline_error",
                            severity="high",
                            description=f"Option deadline after lease expiration for {key}",
                            location="Options section",
                            expected_value="Deadline before expiration",
                            actual_value=f"Deadline: {deadline}, Expiration: {expire}",
                            suggestion="Review option exercise timing requirements"
                        ))
                        
        return issues
        
    def _validate_financial_calculations(self, data: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate financial calculations and consistency"""
        issues = []
        
        # Check base rent calculations
        if 'base_rent' in data and 'rentable_square_feet' in data and 'rent_psf' in data:
            base_rent = self._to_decimal(data['base_rent'])
            rsf = self._to_decimal(data['rentable_square_feet'])
            psf = self._to_decimal(data['rent_psf'])
            
            if base_rent and rsf and psf:
                calculated_rent = rsf * psf
                if abs(calculated_rent - base_rent) / base_rent > self.calculation_tolerance:
                    issues.append(ValidationIssue(
                        issue_type="rent_calculation_mismatch",
                        severity="high",
                        description="Base rent doesn't match PSF calculation",
                        location="Rent section",
                        expected_value=f"${calculated_rent:,.2f}",
                        actual_value=f"${base_rent:,.2f}",
                        suggestion="Verify rent calculation methodology"
                    ))
                    
        # Check CAM calculations
        if 'cam_estimate' in data and 'pro_rata_share' in data and 'total_cam_pool' in data:
            cam = self._to_decimal(data['cam_estimate'])
            share = self._to_decimal(data['pro_rata_share']) / 100
            total = self._to_decimal(data['total_cam_pool'])
            
            if cam and share and total:
                calculated_cam = total * share
                if abs(calculated_cam - cam) / cam > self.calculation_tolerance:
                    issues.append(ValidationIssue(
                        issue_type="cam_calculation_mismatch",
                        severity="medium",
                        description="CAM estimate doesn't match pro-rata calculation",
                        location="CAM section",
                        expected_value=f"${calculated_cam:,.2f}",
                        actual_value=f"${cam:,.2f}",
                        suggestion="Review CAM calculation method"
                    ))
                    
        # Check percentage rent breakpoints
        if 'percentage_rent_breakpoints' in data:
            breakpoints = data['percentage_rent_breakpoints']
            if isinstance(breakpoints, list) and len(breakpoints) > 1:
                # Ensure breakpoints are in ascending order
                for i in range(1, len(breakpoints)):
                    if breakpoints[i]['threshold'] <= breakpoints[i-1]['threshold']:
                        issues.append(ValidationIssue(
                            issue_type="breakpoint_order_error",
                            severity="high",
                            description="Percentage rent breakpoints not in ascending order",
                            location="Percentage Rent section",
                            expected_value="Ascending thresholds",
                            actual_value=f"Breakpoint {i} <= Breakpoint {i-1}",
                            suggestion="Verify breakpoint structure"
                        ))
                        
        return issues
        
    def _validate_cross_references(self, data: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate internal cross-references"""
        issues = []
        references = self._get_all_references(data)
        
        # Check if referenced sections exist
        section_numbers = self._extract_section_numbers(data)
        
        for ref in references:
            ref_section = ref.get('target_section')
            if ref_section and ref_section not in section_numbers:
                issues.append(ValidationIssue(
                    issue_type="broken_reference",
                    severity="medium",
                    description=f"Reference to non-existent section {ref_section}",
                    location=ref.get('source_section', 'Unknown'),
                    expected_value="Valid section reference",
                    actual_value=f"Section {ref_section} not found",
                    suggestion="Check if section numbering has changed"
                ))
                
        return issues
        
    def _validate_defined_terms(self, data: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate defined terms usage"""
        issues = []
        defined_terms = self._get_all_defined_terms(data)
        
        # Check for undefined terms in key provisions
        content_to_check = []
        for key, value in data.items():
            if isinstance(value, dict) and 'content' in value:
                content_to_check.append((key, value['content']))
                
        # Look for capitalized terms that might need definition
        undefined_terms = set()
        for section, content in content_to_check:
            # Find capitalized terms (potential defined terms)
            capitalized = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', content)
            
            for term in capitalized:
                # Skip common words and section references
                if term not in ['The', 'This', 'Section', 'Article', 'Landlord', 'Tenant']:
                    if term not in defined_terms and term not in undefined_terms:
                        undefined_terms.add(term)
                        issues.append(ValidationIssue(
                            issue_type="undefined_term",
                            severity="low",
                            description=f"Potentially undefined term: {term}",
                            location=section,
                            expected_value="Defined term",
                            actual_value="No definition found",
                            suggestion="Verify if term needs definition"
                        ))
                        
        return issues
        
    def _validate_high_stakes_clauses(self, data: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate high-stakes clauses that always need review"""
        issues = []
        
        for clause_type in self.high_stakes_clauses:
            if clause_type in data:
                clause_data = data[clause_type]
                
                # Always flag high-stakes clauses for review
                issues.append(ValidationIssue(
                    issue_type="high_stakes_clause",
                    severity="medium",
                    description=f"High-stakes {clause_type} clause requires careful review",
                    location=f"{clause_type} section",
                    expected_value="Human review completed",
                    actual_value="Pending review",
                    suggestion=f"Legal review recommended for {clause_type} provisions"
                ))
                
                # Check for specific red flags
                if clause_type == 'indemnification':
                    if isinstance(clause_data, dict) and clause_data.get('mutual') is False:
                        issues.append(ValidationIssue(
                            issue_type="one_sided_indemnity",
                            severity="high",
                            description="One-sided indemnification provision detected",
                            location="Indemnification section",
                            expected_value="Mutual indemnification",
                            actual_value="One-way indemnification",
                            suggestion="Consider negotiating mutual indemnification"
                        ))
                        
        return issues
        
    def _validate_amendments(self, data: Dict[str, Any], 
                           document_graph) -> List[ValidationIssue]:
        """Validate amendment application and consistency"""
        issues = []
        
        # Get all amendments for the base document
        base_docs = document_graph.get_base_documents()
        
        for base_doc in base_docs:
            amendments = document_graph.get_amendments_for_document(base_doc.doc_id)
            
            # Check amendment dates are sequential
            for i in range(1, len(amendments)):
                if amendments[i].date and amendments[i-1].date:
                    if amendments[i].date < amendments[i-1].date:
                        issues.append(ValidationIssue(
                            issue_type="amendment_date_order",
                            severity="high",
                            description="Amendments not in chronological order",
                            location=f"Amendment {i+1}",
                            expected_value=f"After {amendments[i-1].date}",
                            actual_value=f"{amendments[i].date}",
                            suggestion="Verify amendment sequence"
                        ))
                        
            # Check for conflicting amendments
            modified_sections = {}
            for amendment in amendments:
                for section in amendment.extracted_data.get('modified_sections', []):
                    if section in modified_sections:
                        issues.append(ValidationIssue(
                            issue_type="conflicting_amendments",
                            severity="medium",
                            description=f"Multiple amendments modify section {section}",
                            location=f"Amendments {modified_sections[section]} and {amendment.doc_id}",
                            expected_value="Clear amendment chain",
                            actual_value="Conflicting modifications",
                            suggestion="Review amendment precedence"
                        ))
                    modified_sections[section] = amendment.doc_id
                    
        return issues
        
    def _validate_cross_document_references(self, data: Dict[str, Any],
                                          document_graph) -> List[ValidationIssue]:
        """Validate references between documents"""
        issues = []
        
        # Find all cross-document references
        cross_refs = document_graph.find_cross_references()
        
        for ref in cross_refs:
            if not ref['resolved']:
                issues.append(ValidationIssue(
                    issue_type="unresolved_document_reference",
                    severity="medium",
                    description=f"Cannot resolve reference: {ref['reference_text']}",
                    location=ref['source_title'],
                    expected_value="Valid document reference",
                    actual_value="Document not found",
                    suggestion="Check if referenced document is missing"
                ))
                
        return issues
        
    def cross_validate_amendments(self, base_data: Dict[str, Any],
                                amendments: List[Dict[str, Any]]) -> ConsistencyReport:
        """
        Validate that amendments properly modify the base document
        """
        issues = []
        warnings = []
        
        current_state = base_data.copy()
        
        for i, amendment in enumerate(amendments):
            # Check what the amendment claims to modify
            for section, new_value in amendment.items():
                if section.startswith('modified_'):
                    original_section = section.replace('modified_', '')
                    
                    if original_section not in current_state:
                        issues.append(ValidationIssue(
                            issue_type="orphaned_amendment",
                            severity="high",
                            description=f"Amendment {i+1} modifies non-existent section",
                            location=f"Amendment {i+1}",
                            expected_value=f"Section {original_section} exists",
                            actual_value="Section not found in base",
                            suggestion="Check if section was added in prior amendment"
                        ))
                    else:
                        # Apply the amendment
                        current_state[original_section] = new_value
                        
        # Additional validation on final state
        final_issues = self.validate_extraction(current_state)
        issues.extend(final_issues.issues)
        
        return ConsistencyReport(
            issues=issues,
            warnings=warnings,
            cross_references_validated=0,
            calculations_validated=0,
            dates_validated=0,
            terms_validated=0,
            overall_score=100 - len(issues) * 5  # Simple scoring
        )
        
    # Helper methods
    def _get_all_dates(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract all dates from the data"""
        dates = {}
        
        def extract_dates(obj, prefix=''):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if any(date_word in key.lower() for date_word in ['date', 'deadline', 'expir', 'commenc']):
                        dates[prefix + key] = value
                    elif isinstance(value, dict):
                        extract_dates(value, prefix + key + '.')
                        
        extract_dates(data)
        return dates
        
    def _get_all_calculations(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract all financial calculations"""
        calculations = []
        
        # Define calculation patterns
        calc_patterns = [
            ('rent', ['base_rent', 'rentable_square_feet', 'rent_psf']),
            ('cam', ['cam_estimate', 'pro_rata_share', 'total_cam_pool']),
            ('security', ['security_deposit', 'months_rent'])
        ]
        
        for calc_name, required_fields in calc_patterns:
            if all(field in data for field in required_fields):
                calculations.append({
                    'type': calc_name,
                    'fields': {field: data[field] for field in required_fields}
                })
                
        return calculations
        
    def _get_all_references(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract all cross-references"""
        references = []
        
        def extract_refs(obj, source=''):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key == 'cross_references' and isinstance(value, list):
                        references.extend(value)
                    elif isinstance(value, str):
                        # Look for section references
                        ref_pattern = r'(?:Section|Article)\s+(\d+(?:\.\d+)*)'
                        for match in re.finditer(ref_pattern, value):
                            references.append({
                                'source_section': source,
                                'target_section': match.group(1),
                                'context': value[max(0, match.start()-50):match.end()+50]
                            })
                    elif isinstance(value, dict):
                        extract_refs(value, key)
                        
        extract_refs(data)
        return references
        
    def _get_all_defined_terms(self, data: Dict[str, Any]) -> Set[str]:
        """Extract all defined terms"""
        defined_terms = set()
        
        if 'defined_terms' in data:
            if isinstance(data['defined_terms'], dict):
                defined_terms.update(data['defined_terms'].keys())
            elif isinstance(data['defined_terms'], list):
                defined_terms.update(data['defined_terms'])
                
        return defined_terms
        
    def _extract_section_numbers(self, data: Dict[str, Any]) -> Set[str]:
        """Extract all section numbers from the document"""
        section_numbers = set()
        
        def extract_sections(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if 'section' in key.lower() and isinstance(value, str):
                        # Extract section number
                        match = re.search(r'(\d+(?:\.\d+)*)', value)
                        if match:
                            section_numbers.add(match.group(1))
                    elif isinstance(value, dict):
                        extract_sections(value)
                        
        extract_sections(data)
        return section_numbers
        
    def _parse_date(self, date_str: Any) -> Optional[date]:
        """Parse date string to date object"""
        if isinstance(date_str, date):
            return date_str
        if isinstance(date_str, datetime):
            return date_str.date()
            
        if isinstance(date_str, str):
            # Try common date formats
            formats = ['%Y-%m-%d', '%m/%d/%Y', '%m-%d-%Y', '%d/%m/%Y']
            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt).date()
                except ValueError:
                    continue
                    
        return None
        
    def _to_decimal(self, value: Any) -> Optional[Decimal]:
        """Convert value to Decimal for precise calculations"""
        if value is None:
            return None
            
        try:
            if isinstance(value, str):
                # Remove currency symbols and commas
                cleaned = re.sub(r'[^\d.\-]', '', value)
                return Decimal(cleaned)
            else:
                return Decimal(str(value))
        except:
            return None
