"""
Dynamic Summary Generator - Generates summaries that adapt to available data
"""

from typing import List, Dict, Any
import json
from app.utils.logger import logger


def generate_dynamic_summary(chunks: List[Dict[str, Any]]) -> str:
    """
    Generate a dynamic summary that adapts to the available data
    """
    if not chunks:
        return generate_empty_summary()
    
    # Analyze what data we have
    available_data = analyze_available_data(chunks)
    
    # Generate appropriate summary based on available data
    if available_data['has_minimal_data']:
        return generate_minimal_data_summary(chunks, available_data)
    else:
        return generate_full_summary(chunks, available_data)


def analyze_available_data(chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze what data is available in the chunks"""
    analysis = {
        'has_parties': False,
        'has_premises': False,
        'has_financial': False,
        'has_term': False,
        'has_minimal_data': True,
        'total_fields': 0,
        'clause_types': set(),
        'has_risks': False,
        'document_type': None
    }
    
    for chunk in chunks:
        clause_hint = chunk.get('clause_hint', '').lower()
        key_values = chunk.get('key_values', {})
        risk_flags = chunk.get('risk_flags', [])
        
        if key_values:
            analysis['total_fields'] += len(key_values)
            
        analysis['clause_types'].add(clause_hint)
        
        if 'parties' in clause_hint:
            analysis['has_parties'] = bool(key_values)
        elif 'premises' in clause_hint:
            analysis['has_premises'] = bool(key_values)
        elif 'rent' in clause_hint or 'financial' in clause_hint:
            analysis['has_financial'] = bool(key_values)
        elif 'term' in clause_hint:
            analysis['has_term'] = bool(key_values)
        elif 'document_overview' in clause_hint:
            analysis['document_type'] = key_values.get('document_type', 'lease')
            
        if risk_flags:
            analysis['has_risks'] = True
    
    # Determine if we have minimal data
    analysis['has_minimal_data'] = analysis['total_fields'] < 5
    
    return analysis


def generate_empty_summary() -> str:
    """Generate summary when no data is available"""
    return """# Lease Summary

## ⚠️ No Data Extracted

The system was unable to extract any lease information from this document.

**Possible Reasons:**
- The document may not be a lease agreement
- The PDF may be corrupted or unreadable
- The document may be heavily scanned with poor text quality

**Recommended Actions:**
1. Verify the document is a complete lease agreement
2. Check if the PDF has selectable text
3. Try uploading a clearer version of the document
4. Contact support if the issue persists
"""


def generate_minimal_data_summary(chunks: List[Dict[str, Any]], analysis: Dict[str, Any]) -> str:
    """Generate summary when minimal data is available"""
    summary = "# Lease Document Analysis\n\n"
    
    # Add warning about limited extraction
    summary += "## ⚠️ Limited Information Extracted\n\n"
    summary += "The automated extraction found limited information in this document. "
    summary += "Below is a summary of the data that could be extracted.\n\n"
    
    # Add any extracted data
    if analysis['total_fields'] > 0:
        summary += "## 📋 Extracted Information\n\n"
        
        for chunk in chunks:
            clause_hint = chunk.get('clause_hint', 'unknown')
            key_values = chunk.get('key_values', {})
            
            if key_values:
                # Format clause name
                clause_name = clause_hint.replace('_', ' ').title()
                summary += f"### {clause_name}\n\n"
                
                # Add key-value pairs
                for key, value in key_values.items():
                    if value and str(value).lower() not in ['null', 'none', 'not found']:
                        formatted_key = key.replace('_', ' ').title()
                        summary += f"- **{formatted_key}**: {value}\n"
                
                summary += "\n"
    
    # Add document overview if available
    for chunk in chunks:
        if 'document_overview' in chunk.get('clause_hint', ''):
            key_values = chunk.get('key_values', {})
            if key_values:
                summary += "## 📄 Document Overview\n\n"
                
                if key_values.get('document_type'):
                    summary += f"- **Document Type**: {key_values['document_type']}\n"
                if key_values.get('page_count'):
                    summary += f"- **Total Pages**: {key_values['page_count']}\n"
                if key_values.get('word_count'):
                    summary += f"- **Word Count**: {key_values['word_count']:,}\n"
                    
                # Add dates found
                dates_found = key_values.get('dates_found', [])
                if dates_found:
                    summary += f"\n**Dates Found in Document**:\n"
                    for date in dates_found[:5]:  # Limit to first 5
                        summary += f"- {date}\n"
                
                # Add amounts found
                amounts_found = key_values.get('amounts_found', [])
                if amounts_found:
                    summary += f"\n**Dollar Amounts Found**:\n"
                    for amount in amounts_found[:5]:  # Limit to first 5
                        summary += f"- ${amount}\n"
                
                summary += "\n"
                break
    
    # Add risks if any
    all_risks = []
    for chunk in chunks:
        risk_flags = chunk.get('risk_flags', [])
        for risk in risk_flags:
            if risk.get('risk_level', '').lower() in ['medium', 'high']:
                all_risks.append(risk)
    
    if all_risks:
        summary += "## ⚠️ Risk Flags\n\n"
        for risk in all_risks:
            level = risk.get('risk_level', 'medium').upper()
            desc = risk.get('description', 'Risk identified')
            summary += f"- **{level}**: {desc}\n"
        summary += "\n"
    
    # Add recommendations
    summary += "## 💡 Recommendations\n\n"
    summary += "Due to the limited automated extraction:\n\n"
    summary += "1. **Manual Review Required**: Please review the original document for complete information\n"
    summary += "2. **Key Areas to Check**: Parties, premises, rent, term, and other essential lease provisions\n"
    summary += "3. **Consider Re-upload**: If this is a scanned document, try uploading a clearer version\n"
    
    return summary


def generate_full_summary(chunks: List[Dict[str, Any]], analysis: Dict[str, Any]) -> str:
    """Generate a comprehensive summary when good data is available"""
    summary = "# Lease Summary\n\n"
    
    # Group chunks by section
    sections = group_chunks_by_section(chunks)
    
    # 1. Lease Overview
    if 'parties' in sections or 'premises' in sections:
        summary += "## 📄 Lease Overview\n\n"
        
        # Add parties information
        if 'parties' in sections:
            for chunk in sections['parties']:
                kv = chunk.get('key_values', {})
                if kv.get('landlord_name') or kv.get('landlord'):
                    summary += f"**Landlord**: {kv.get('landlord_name') or kv.get('landlord')}\n\n"
                if kv.get('tenant_name') or kv.get('tenant'):
                    summary += f"**Tenant**: {kv.get('tenant_name') or kv.get('tenant')}\n\n"
        
        # Add premises information
        if 'premises' in sections:
            for chunk in sections['premises']:
                kv = chunk.get('key_values', {})
                if kv.get('address'):
                    summary += f"**Property Address**: {kv.get('address')}\n\n"
                if kv.get('square_feet') or kv.get('square_footage'):
                    sq_ft = kv.get('square_feet') or kv.get('square_footage')
                    summary += f"**Square Footage**: {sq_ft}\n\n"
                if kv.get('suite'):
                    summary += f"**Suite/Unit**: {kv.get('suite')}\n\n"
    
    # 2. Lease Term
    if 'term' in sections:
        summary += "## 📅 Lease Term\n\n"
        for chunk in sections['term']:
            kv = chunk.get('key_values', {})
            if kv.get('commencement_date'):
                summary += f"**Commencement Date**: {kv.get('commencement_date')}\n\n"
            if kv.get('expiration_date'):
                summary += f"**Expiration Date**: {kv.get('expiration_date')}\n\n"
            if kv.get('term_length') or kv.get('term'):
                term = kv.get('term_length') or kv.get('term')
                summary += f"**Term Length**: {term}\n\n"
    
    # 3. Rent & Payments
    if 'rent' in sections or any('rent' in k for k in sections.keys()):
        summary += "## 💰 Rent & Payments\n\n"
        for key in sections:
            if 'rent' in key:
                for chunk in sections[key]:
                    kv = chunk.get('key_values', {})
                    if kv.get('base_rent') or kv.get('monthly_rent'):
                        rent = kv.get('base_rent') or kv.get('monthly_rent')
                        summary += f"**Base Rent**: {rent}\n\n"
                    if kv.get('annual_rent'):
                        summary += f"**Annual Rent**: {kv.get('annual_rent')}\n\n"
                    if kv.get('escalation') or kv.get('escalation_rate'):
                        esc = kv.get('escalation') or kv.get('escalation_rate')
                        summary += f"**Rent Escalation**: {esc}\n\n"
    
    # 4. Security Deposit
    if 'security' in sections:
        summary += "## 🔐 Security Deposit\n\n"
        for chunk in sections['security']:
            kv = chunk.get('key_values', {})
            if kv.get('amount') or kv.get('security_deposit'):
                amount = kv.get('amount') or kv.get('security_deposit')
                summary += f"**Security Deposit**: {amount}\n\n"
    
    # 5. Use of Premises
    if 'use' in sections:
        summary += "## 🏢 Use of Premises\n\n"
        for chunk in sections['use']:
            kv = chunk.get('key_values', {})
            if kv.get('permitted_use'):
                summary += f"**Permitted Use**: {kv.get('permitted_use')}\n\n"
    
    # 6. Other Clauses
    other_sections = {k: v for k, v in sections.items() 
                     if k not in ['parties', 'premises', 'term', 'rent', 'security', 'use']}
    
    if other_sections:
        summary += "## 📜 Additional Provisions\n\n"
        for section_name, section_chunks in other_sections.items():
            if section_chunks:
                # Format section name
                formatted_name = section_name.replace('_', ' ').title()
                summary += f"### {formatted_name}\n\n"
                
                for chunk in section_chunks:
                    kv = chunk.get('key_values', {})
                    for key, value in kv.items():
                        if value and str(value).lower() not in ['null', 'none']:
                            formatted_key = key.replace('_', ' ').title()
                            summary += f"- **{formatted_key}**: {value}\n"
                
                summary += "\n"
    
    # 7. Risk Analysis
    all_risks = []
    for chunk in chunks:
        risk_flags = chunk.get('risk_flags', [])
        for risk in risk_flags:
            if risk.get('risk_level', '').lower() in ['medium', 'high']:
                all_risks.append(risk)
    
    if all_risks:
        summary += "## ⚠️ Risk Analysis\n\n"
        
        # Group by risk level
        high_risks = [r for r in all_risks if r.get('risk_level', '').lower() == 'high']
        medium_risks = [r for r in all_risks if r.get('risk_level', '').lower() == 'medium']
        
        if high_risks:
            summary += "### High Priority Risks\n\n"
            for risk in high_risks:
                desc = risk.get('description', 'Risk identified')
                summary += f"- {desc}\n"
            summary += "\n"
        
        if medium_risks:
            summary += "### Medium Priority Risks\n\n"
            for risk in medium_risks:
                desc = risk.get('description', 'Risk identified')
                summary += f"- {desc}\n"
            summary += "\n"
    
    # 8. Data Quality Notice
    low_confidence_count = sum(1 for chunk in chunks if chunk.get('confidence', 1.0) < 0.5)
    if low_confidence_count > 0:
        summary += "## 📊 Data Quality Notice\n\n"
        summary += f"**Note**: {low_confidence_count} clause(s) were extracted with low confidence and may need verification.\n\n"
    
    return summary


def group_chunks_by_section(chunks: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Group chunks by their clause type for organized presentation"""
    sections = {}
    
    for chunk in chunks:
        clause_hint = chunk.get('clause_hint', 'unknown').lower()
        
        # Normalize clause hints to common sections
        if 'parties' in clause_hint:
            section = 'parties'
        elif 'premises' in clause_hint:
            section = 'premises'
        elif 'term' in clause_hint:
            section = 'term'
        elif 'rent' in clause_hint:
            section = 'rent'
        elif 'security' in clause_hint:
            section = 'security'
        elif 'use' in clause_hint:
            section = 'use'
        elif 'insurance' in clause_hint:
            section = 'insurance'
        elif 'maintenance' in clause_hint:
            section = 'maintenance'
        elif 'assignment' in clause_hint:
            section = 'assignment'
        else:
            section = clause_hint
        
        if section not in sections:
            sections[section] = []
        
        sections[section].append(chunk)
    
    return sections
