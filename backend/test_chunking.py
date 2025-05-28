#!/usr/bin/env python3
"""
Test script to verify the chunking system works properly
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.schemas import LeaseType
from app.core.advanced_chunker import chunk_lease

# Test with a simple lease text
test_text = """
LEASE AGREEMENT

ARTICLE I: PREMISES

Landlord hereby leases to Tenant and Tenant hereby leases from Landlord the premises described as:
1818 McKee St, San Diego, California 92110 (the "Premises").

ARTICLE II: TERM

The term of this lease shall be for a period of 12 months, commencing on January 1, 2025 
and ending on December 31, 2025.

ARTICLE III: RENT

Tenant agrees to pay to Landlord as rent for the Premises the sum of $3,000 per month,
payable in advance on the first day of each month.

ARTICLE IV: USE OF PREMISES

The Premises shall be used and occupied by Tenant exclusively as a residential dwelling.
No commercial activities shall be conducted on the Premises.

ARTICLE V: MAINTENANCE

Tenant shall maintain the Premises in good condition and shall be responsible for 
minor repairs under $100. Landlord shall be responsible for major repairs.
"""

def test_chunking():
    print("Testing chunking system...")
    print(f"Text length: {len(test_text)} characters")
    
    try:
        # Test chunking
        chunks = chunk_lease(test_text, LeaseType.RETAIL)
        
        print(f"\nSuccessfully created {len(chunks)} chunks:")
        for i, chunk in enumerate(chunks):
            print(f"\nChunk {i+1}:")
            print(f"  ID: {chunk.get('chunk_id')}")
            print(f"  Type: {chunk.get('clause_hint')}")
            print(f"  Confidence: {chunk.get('confidence')}")
            print(f"  Content preview: {chunk.get('content', '')[:100]}...")
            
    except Exception as e:
        print(f"\nError during chunking: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Set OpenAI API key if not already set
    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY environment variable not set")
        sys.exit(1)
    
    test_chunking()
