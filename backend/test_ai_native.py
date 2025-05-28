"""
Test script for AI-Native Lease Extraction System

This script demonstrates the fully AI-native extraction capabilities.
"""

import asyncio
import os
from app.schemas import LeaseType
from app.core.ai_native_extractor import AILeaseIntelligence
from app.core.ai_advanced_chunker import AIAdvancedChunker
from app.core.ai_specialized_extractors import (
    AIFinancialClauseExtractor,
    AIDateTimeExtractor,
    AIConditionalClauseExtractor,
    AIRightsAndOptionsExtractor
)
from app.utils.logger import logger


async def test_ai_native_extraction():
    """Test the complete AI-native extraction pipeline"""
    
    # Sample lease text (simplified for testing)
    lease_text = """
    OFFICE LEASE AGREEMENT
    
    This Lease Agreement is entered into as of January 15, 2025, between 
    PACIFIC TOWERS LLC, a California limited liability company ("Landlord") and 
    TECHCORP INNOVATIONS, INC., a Delaware corporation ("Tenant").
    
    PREMISES: Suite 1500, consisting of approximately 12,500 rentable square feet 
    on the fifteenth floor of the building located at 555 California Street, 
    San Francisco, CA 94104.
    
    TERM: The lease term shall commence on March 1, 2025 and expire on February 28, 2030,
    unless sooner terminated in accordance with the provisions hereof.
    
    BASE RENT: Tenant shall pay base rent as follows:
    - Year 1: $62.50 per rentable square foot annually ($65,104.17 monthly)
    - Years 2-3: $64.38 per rentable square foot annually  
    - Years 4-5: $66.31 per rentable square foot annually
    
    OPERATING EXPENSES: Tenant shall pay its Proportionate Share (which is 8.2%) 
    of Operating Expenses in excess of the Base Year (2025) amount. Operating 
    Expenses are estimated at $15.00 per square foot for 2025.
    
    RENEWAL OPTION: Provided Tenant is not in default, Tenant shall have one (1) 
    option to renew this Lease for an additional five (5) year term at ninety-five 
    percent (95%) of the then-prevailing market rent. Tenant must provide written 
    notice of its intent to renew not less than nine (9) months nor more than 
    twelve (12) months prior to the expiration of the initial term.
    
    PARKING: Tenant shall have the right to lease up to forty (40) parking spaces 
    in the building garage at the prevailing monthly rates.
    
    CONDITION: If Landlord cannot deliver possession of the Premises on the 
    Commencement Date, Landlord shall not be liable for any damage, but the 
    rental herein provided shall be abated until possession is given.
    """
    
    # Initialize AI system
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("OpenAI API key not found in environment")
        return
    
    print("\n=== Testing AI-Native Lease Extraction System ===\n")
    
    # Test 1: AI-Native Chunking
    print("1. Testing AI-Native Chunking...")
    chunker = AIAdvancedChunker(lease_text, LeaseType.OFFICE, api_key)
    chunks = await chunker.process()
    
    print(f"   - Found {len(chunks)} intelligent chunks")
    for chunk in chunks[:3]:  # Show first 3
        print(f"   - Chunk: {chunk['clause_hint']} (Confidence: {chunk['confidence']})")
    
    # Test 2: Complete AI Extraction
    print("\n2. Testing Complete AI Extraction Pipeline...")
    ai_system = AILeaseIntelligence(api_key)
    
    pdf_content = {
        'text': lease_text,
        'layout_info': {'segments': chunks}
    }
    
    results = await ai_system.extract_complete_lease_intelligence(
        pdf_content,
        LeaseType.OFFICE
    )
    
    print(f"   - Extraction confidence: {results['metadata']['confidence_score']:.2f}")
    print(f"   - Clauses extracted: {len(results['extracted_clauses'])}")
    
    # Test 3: Specialized AI Extractors
    print("\n3. Testing AI Specialized Extractors...")
    
    # Financial extraction
    financial_extractor = AIFinancialClauseExtractor()
    rent_section = "BASE RENT: Tenant shall pay base rent as follows:\n- Year 1: $62.50 per rentable square foot annually ($65,104.17 monthly)"
    
    financial_result = await financial_extractor.extract_base_rent(rent_section)
    print(f"   - Financial extraction confidence: {financial_result.confidence}")
    print(f"   - Base rent found: {financial_result.extracted_data.get('base_rent_amount')}")
    
    # Date extraction
    date_extractor = AIDateTimeExtractor()
    dates_result = await date_extractor.extract_critical_dates(lease_text)
    print(f"   - Date extraction confidence: {dates_result.confidence}")
    print(f"   - Commencement date: {dates_result.extracted_data.get('key_dates', {}).get('lease_commencement')}")
    
    # Rights extraction
    rights_extractor = AIRightsAndOptionsExtractor()
    rights_result = await rights_extractor.extract_all_options(lease_text)
    print(f"   - Rights extraction confidence: {rights_result.confidence}")
    print(f"   - Renewal options found: {len(rights_result.extracted_data.get('renewal_options', []))}")
    
    # Test 4: Risk Analysis
    print("\n4. AI Risk Analysis Results:")
    risk_analysis = results.get('risk_analysis', {})
    if risk_analysis:
        print(f"   - Total risks identified: {len(risk_analysis.get('risks', []))}")
        for risk in risk_analysis.get('risks', [])[:3]:
            print(f"   - {risk.get('level', 'Unknown')}: {risk.get('description', '')}")
    
    # Test 5: Completeness Check
    print("\n5. AI Completeness Analysis:")
    completeness = results.get('completeness_report', {})
    if completeness:
        print(f"   - Completeness score: {completeness.get('score', 0):.2f}")
        missing = completeness.get('missing_provisions', [])
        if missing:
            print(f"   - Missing provisions: {', '.join(missing[:3])}")
    
    print("\n=== AI-Native Extraction Complete ===\n")
    
    # Show extraction example
    print("Example Extracted Data:")
    if results['extracted_clauses']:
        first_clause = list(results['extracted_clauses'].items())[0]
        print(f"\nClause: {first_clause[0]}")
        print(f"Data: {json.dumps(first_clause[1], indent=2)[:500]}...")


async def test_edge_cases():
    """Test AI system with edge cases"""
    
    print("\n=== Testing Edge Cases ===\n")
    
    # Test with ambiguous language
    ambiguous_text = """
    The tenant may or may not have the option to renew, subject to various 
    conditions that shall be determined at a later date, unless otherwise 
    specified in writing by either party, notwithstanding any verbal agreements.
    """
    
    api_key = os.environ.get("OPENAI_API_KEY")
    ai_system = AILeaseIntelligence(api_key)
    
    # Test extraction
    pdf_content = {'text': ambiguous_text, 'layout_info': {}}
    results = await ai_system.extract_complete_lease_intelligence(
        pdf_content,
        LeaseType.OFFICE
    )
    
    print("1. Ambiguous Language Test:")
    print(f"   - AI understood the ambiguity: {results['metadata']['confidence_score'] < 0.7}")
    
    # Test with missing information
    incomplete_text = """
    LEASE AGREEMENT
    
    Landlord: [TO BE DETERMINED]
    Tenant: ACME Corp
    Rent: $_____ per month
    Term: ___ years commencing on ______
    """
    
    pdf_content = {'text': incomplete_text, 'layout_info': {}}
    results = await ai_system.extract_complete_lease_intelligence(
        pdf_content,
        LeaseType.OFFICE
    )
    
    print("\n2. Incomplete Document Test:")
    print(f"   - Identified missing information: {len(results.get('completeness_report', {}).get('missing_information', [])) > 0}")
    
    print("\n=== Edge Case Testing Complete ===")


if __name__ == "__main__":
    # Run tests
    asyncio.run(test_ai_native_extraction())
    asyncio.run(test_edge_cases())
