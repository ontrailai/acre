"""
Test script for the advanced chunking system.
This script demonstrates and validates the advanced chunking functionality.
Run this script directly to test the chunking on sample lease text.
"""

import sys
import os
import json
from pprint import pprint

# Add the parent directory to the Python path to import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.advanced_chunker import chunk_lease
from app.schemas import LeaseType

def run_chunking_test():
    """Run a test of the advanced chunking system on a sample lease excerpt"""
    print("Running advanced chunking test...")
    
    # Sample lease excerpt (simplified for testing)
    sample_lease = """
    LEASE AGREEMENT
    
    THIS LEASE AGREEMENT (this "Lease") is made and entered into as of January 15, 2023 (the "Effective Date"), by and between ACME PROPERTIES LLC, a Delaware limited liability company ("Landlord"), and TENANT CORPORATION, a California corporation ("Tenant").
    
    WITNESSETH:
    
    WHEREAS, Landlord is the owner of that certain building located at 123 Main Street, Anytown, CA 90210 (the "Building"); and
    
    WHEREAS, Tenant desires to lease certain space in the Building, and Landlord desires to lease such space to Tenant, all on the terms and conditions hereinafter set forth;
    
    NOW, THEREFORE, in consideration of the mutual covenants and agreements herein contained, the parties hereto agree as follows:
    
    ARTICLE 1. PREMISES
    
    1.1 Landlord hereby leases to Tenant, and Tenant hereby leases from Landlord, that certain space consisting of approximately 5,000 rentable square feet located on the 3rd floor of the Building, as more particularly shown on Exhibit A attached hereto (the "Premises").
    
    1.2 Tenant shall have the non-exclusive right to use the common areas of the Building in common with other tenants of the Building.
    
    ARTICLE 2. TERM
    
    2.1 The term of this Lease (the "Term") shall commence on March 1, 2023 (the "Commencement Date") and shall expire on February 28, 2028 (the "Expiration Date"), unless sooner terminated as provided herein.
    
    2.2 Tenant shall have the option to extend the Term for one (1) additional period of five (5) years, provided that Tenant is not in default under this Lease at the time of exercise of such option.
    
    ARTICLE 3. BASE RENT
    
    3.1 Tenant shall pay to Landlord, as base rent for the Premises, the following amounts:
    
    Period             Monthly Base Rent    Annual Base Rent
    ----------------- ------------------- -----------------
    Year 1             $12,500.00          $150,000.00
    Year 2             $12,875.00          $154,500.00
    Year 3             $13,261.25          $159,135.00
    Year 4             $13,659.09          $163,909.05
    Year 5             $14,068.86          $168,826.32
    
    3.2 Base Rent shall be paid in advance on the first day of each and every calendar month during the Term.
    
    ARTICLE 4. ADDITIONAL RENT
    
    4.1 In addition to Base Rent, Tenant shall pay to Landlord as additional rent Tenant's Share of Operating Expenses as provided in this Article 4.
    
    4.2 "Operating Expenses" shall mean all costs and expenses incurred by Landlord in the ownership, operation, maintenance, repair and management of the Building, including, but not limited to:
    
    (a) Real Property Taxes;
    (b) Insurance premiums;
    (c) Utilities;
    (d) Repair and maintenance costs;
    (e) Management fees.
    
    ARTICLE 5. USE OF PREMISES
    
    5.1 Tenant shall use the Premises solely for general office purposes and for no other purpose without the prior written consent of Landlord.
    
    5.2 Tenant shall not use or occupy the Premises in violation of any applicable laws, regulations, rules or ordinances.
    
    ARTICLE 6. MAINTENANCE AND REPAIRS
    
    6.1 Landlord shall maintain and keep in good repair the structural portions of the Building, including the foundation, exterior walls, structural portions of the roof, and the common areas of the Building.
    
    6.2 Tenant shall maintain and keep in good repair the interior, non-structural portions of the Premises, including all fixtures, equipment and appurtenances therein.
    
    ARTICLE 7. ASSIGNMENT AND SUBLETTING
    
    7.1 Tenant shall not assign this Lease or sublet all or any part of the Premises without the prior written consent of Landlord, which consent shall not be unreasonably withheld, conditioned or delayed.
    
    7.2 Any assignment or subletting without Landlord's consent shall be void and shall constitute a default under this Lease.
    
    ARTICLE 8. INSURANCE
    
    8.1 Tenant shall maintain, at its sole cost and expense, the following insurance during the Term:
    
    (a) Commercial general liability insurance with limits of not less than $2,000,000 per occurrence;
    (b) Property insurance covering Tenant's personal property;
    (c) Worker's compensation insurance as required by law.
    
    IN WITNESS WHEREOF, the parties hereto have executed this Lease as of the Effective Date.
    
    LANDLORD:                             TENANT:
    ACME PROPERTIES LLC                   TENANT CORPORATION
    
    By: ________________________          By: ________________________
    Name:                                 Name:
    Title:                                Title:
    """
    
    # Run the chunking system
    chunks = chunk_lease(sample_lease, LeaseType.OFFICE)
    
    # Create a debug directory
    debug_dir = "test_output"
    os.makedirs(debug_dir, exist_ok=True)
    
    # Save the chunks to a file for inspection
    with open(os.path.join(debug_dir, "test_chunks.json"), "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2, default=str)
    
    # Print summary of chunks
    print(f"\nChunking complete! Generated {len(chunks)} chunks:")
    for i, chunk in enumerate(chunks):
        print(f"\nChunk {i+1} - {chunk['chunk_id']}:")
        print(f"  Section: {chunk.get('clause_hint', 'undefined')}")
        print(f"  Pages: {chunk.get('page_start')} - {chunk.get('page_end')}")
        print(f"  Is Table: {chunk.get('is_table', False)}")
        print(f"  Token Estimate: {chunk.get('token_estimate', 0)}")
        print(f"  Parent Heading: {chunk.get('parent_heading', 'None')}")
        content_preview = chunk.get('content', '')[:50].replace('\n', ' ')
        print(f"  Content: {content_preview}...")

    print(f"\nDetailed results saved to {os.path.abspath(os.path.join(debug_dir, 'test_chunks.json'))}")
    return chunks

if __name__ == "__main__":
    # Run the test
    chunks = run_chunking_test()
    
    # Analyze the results
    total_tokens = sum(chunk.get('token_estimate', 0) for chunk in chunks)
    tables = [chunk for chunk in chunks if chunk.get('is_table', False)]
    
    print("\n=== ANALYSIS ===")
    print(f"Total chunks: {len(chunks)}")
    print(f"Total estimated tokens: {total_tokens}")
    print(f"Tables found: {len(tables)}")
    
    # Check clause coverage
    clauses = {}
    for chunk in chunks:
        clause = chunk.get('clause_hint', 'undefined')
        if clause in clauses:
            clauses[clause] += 1
        else:
            clauses[clause] = 1
    
    print("\nClause coverage:")
    for clause, count in clauses.items():
        print(f"  {clause}: {count} chunk(s)")
    
    # Check for any chunks that might be too large
    large_chunks = [chunk for chunk in chunks if chunk.get('token_estimate', 0) > 1000]
    if large_chunks:
        print(f"\nWARNING: {len(large_chunks)} chunks exceed 1000 tokens:")
        for chunk in large_chunks:
            print(f"  {chunk['chunk_id']}: {chunk.get('token_estimate')} tokens, {chunk.get('clause_hint')} clause")
    else:
        print("\nGood! No chunks exceed 1000 tokens.")
