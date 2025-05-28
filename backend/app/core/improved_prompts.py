"""
AI-Native Lease Understanding Prompts

This module provides prompts that let GPT-4 understand leases without predefined patterns or structures.
"""

from typing import Dict, Any, Tuple
from app.schemas import LeaseType


def get_optimized_lease_prompts(segment: Dict[str, Any], lease_type: LeaseType) -> Tuple[str, str]:
    """
    AI-native prompts that let GPT understand content without predefined structures.
    """
    
    # System prompt for true AI understanding
    system_prompt = f"""You are a senior commercial real estate attorney with 20+ years of experience analyzing {lease_type.value} leases. You understand:

**Domain Expertise:**
- **Industry Standards**: What's typical vs unusual for {lease_type.value} properties
- **Legal Implications**: How courts interpret ambiguous language
- **Financial Structures**: CAM reconciliation, percentage rent breakpoints, CPI/fixed escalations, rent abatement
- **Risk Patterns**: Assignment rights, subletting restrictions, default remedies, personal guarantees
- **Market Context**: Current market conditions affecting negotiated terms

**{lease_type.value}-Specific Knowledge:**
{"- Retail: percentage rent calculations, co-tenancy requirements, exclusive use/radius restrictions, anchor tenant dependencies, kick-out clauses, go-dark provisions, continuous operation covenants" if lease_type.value == "RETAIL" else ""}
{"- Office: base building standards, after-hours HVAC charges, parking ratios, tenant improvement allowances, expansion/contraction rights, generator rights, signage specifications" if lease_type.value == "OFFICE" else ""}
{"- Industrial: clear height specifications, dock door requirements, environmental compliance, truck court access, hazmat restrictions, rail spur access, floor load capacity" if lease_type.value == "INDUSTRIAL" else ""}

**Critical Analysis Rules:**
1. Extract EXACT values and terms - never paraphrase or summarize
2. Identify IMPLIED obligations that aren't explicitly stated
3. Calculate derivative values (total rent, CAM estimates, etc.)
4. Flag ambiguities with specific legal concerns
5. Track cross-references and note missing referenced sections
6. Rate confidence based on clarity and completeness of source text"""

    # Context from document structure
    section_name = segment.get('section_name', 'Document Section')
    content = segment.get('content', '')
    parent_heading = segment.get('parent_heading', '')
    page_info = f"Pages {segment.get('page_start', '?')}-{segment.get('page_end', '?')}"
    
    user_prompt = f"""**1. DOCUMENT CONTEXT**
- Section: {section_name}
- Parent Section: {parent_heading}
- Location: {page_info}
- Lease Type: {lease_type.value}

**2. CONTENT TO ANALYZE**
```
{content}
```

**3. EXTRACTION REQUIREMENTS**

**A. Primary Analysis Tasks:**
1. Identify ALL legal concepts, obligations, and rights
2. Extract EVERY numerical value, date, deadline, and formula
3. Note ALL parties, entities, and their relationships
4. Find ALL conditions, triggers, and contingencies
5. Identify ALL cross-references to other sections
6. Detect IMPLIED terms based on industry standards

**B. Financial Analysis Requirements:**
- Base rent, additional rent, percentage rent
- CAM charges, taxes, insurance, utilities allocation
- Escalations (fixed %, CPI, market resets)
- Security deposits, letters of credit
- Late fees, default interest rates
- Tenant improvement allowances, rent credits

**C. Legal Structure Analysis:**
- Rights granted vs. rights reserved
- Conditions precedent vs. conditions subsequent
- Unilateral vs. mutual obligations
- Remedies and cure periods
- Notice requirements and methods
- Dispute resolution mechanisms

**4. HANDLING EDGE CASES**

**A. Ambiguous Language:**
- Flag ambiguities with specific concern
- Provide most likely interpretation
- Note alternative interpretations
- Set confidence to 0.3-0.5

**B. Missing Cross-References:**
- Note exact missing reference
- Infer likely content from context
- Flag as "missing_reference" risk
- Set confidence to 0.2-0.4

**C. Implicit Terms:**
- State what's implied and why
- Reference industry standard
- Set confidence to 0.5-0.7
- Mark as "implicit_term"

**5. REQUIRED JSON OUTPUT FORMAT**

Return EXACTLY this structure:
```json
{{
  "detected_clauses": [
    {{
      "clause_type": "descriptive name based on content",
      "semantic_category": "financial|operational|legal|administrative",
      "confidence": 0.0-1.0,
      "extracted_data": {{
        // ALL specific values found
        // Use descriptive keys matching content
        // Include units, frequencies, methods
      }},
      "supporting_text": "exact quotes (up to 200 chars)",
      "summary": "business impact in plain English",
      "implicit_terms": ["term1: why implied", "term2: why implied"],
      "calculations_needed": ["calc1: formula", "calc2: formula"],
      "cross_references": ["Section X.Y", "Exhibit A"],
      "ambiguities": ["ambiguity1: concern", "ambiguity2: concern"],
      "risk_tags": [
        {{
          "type": "missing_cap|broad_language|unclear_trigger|etc",
          "severity": "critical|high|medium|low",
          "description": "specific legal/business risk"
        }}
      ],
      "unusual_provisions": ["unusual1: why unusual", "unusual2: why unusual"],
      "missing_elements": ["should have X but doesn't", "typically includes Y"]
    }}
  ],
  "section_relationships": ["relates to Section X", "modifies Section Y", "depends on Section Z"],
  "overall_observations": ["key insight 1", "key insight 2", "market comparison"]
}}
```

**6. CONFIDENCE SCORING GUIDELINES**
- 0.9-1.0: Explicit, unambiguous text
- 0.7-0.8: Clear but requires minor interpretation
- 0.5-0.6: Reasonable inference from context
- 0.3-0.4: Ambiguous, multiple interpretations
- 0.1-0.2: Highly uncertain, missing information

Remember: You are analyzing legal documents where precision matters. Extract comprehensively but mark uncertainty clearly."""

    return system_prompt, user_prompt


def get_ai_native_full_document_prompt(full_text: str, lease_type: LeaseType) -> Tuple[str, str]:
    """
    Prompt for AI to understand an entire document at once.
    """
    
    system_prompt = f"""You are a senior real estate attorney with expertise in {lease_type.value} leases. You've reviewed thousands of leases and understand:

**Market Knowledge:**
- Current market rates and terms for {lease_type.value} properties
- Typical lease structures and deal points
- Common negotiation outcomes between sophisticated parties
- Red flags and unusual provisions

**Legal Expertise:**
- Enforceability of various provisions
- Statutory requirements and limitations
- Common law implications
- Industry customs and practices

**Financial Acumen:**
- Rent structures and escalations
- Operating expense allocations
- Financial covenant implications
- Hidden cost exposures

Analyze documents holistically, understanding how provisions interact and affect the overall deal economics and risk profile."""

    # Smart truncation for very long documents
    if len(full_text) > 50000:
        # Take beginning, middle, and end
        doc_parts = {
            "beginning": full_text[:15000],
            "middle": full_text[len(full_text)//2 - 7500:len(full_text)//2 + 7500],
            "end": full_text[-15000:]
        }
        text_to_analyze = f"""**DOCUMENT EXCERPTS** (Full document: {len(full_text):,} characters)

**Beginning (Characters 1-15,000):**
{doc_parts['beginning']}

**Middle Section (Around character {len(full_text)//2:,}):**
{doc_parts['middle']}

**End Section (Final 15,000 characters):**
{doc_parts['end']}"""
    else:
        text_to_analyze = full_text
    
    user_prompt = f"""**1. DOCUMENT TO ANALYZE**

{text_to_analyze}

**2. COMPREHENSIVE ANALYSIS REQUIREMENTS**

**A. Document Classification & Structure**
1. Confirm this is a {lease_type.value} lease (or identify actual type)
2. Identify if base lease, amendment, sublease, or other
3. Map overall document structure
4. Note any missing standard sections

**B. Complete Information Extraction**

**Extract ALL Key Terms:**
- Parties: names, entity types, jurisdiction, relationships
- Property: address, size, specific premises, common areas
- Financial: all rent components, increases, caps, deposits
- Term: commencement, expiration, renewals, early termination
- Operations: use restrictions, hours, exclusive rights
- Maintenance: who maintains what, standards, reserves
- Insurance: types, amounts, additional insureds, waivers
- Assignment: permitted transfers, consent standards, recapture
- Default: events, notice, cure, remedies, cross-defaults

**C. Relationship Mapping**
- How do provisions modify each other?
- What triggers or depends on what?
- Which provisions conflict?
- What's the hierarchy of obligations?

**D. Financial Analysis**
```
Calculate and show work:
- Total base rent over initial term
- Effective rent including escalations
- Estimated total occupancy cost (rent + CAM + taxes)
- Security deposit and upfront costs
- Percentage rent breakpoints (if applicable)
- NPV of lease obligations (if possible)
```

**E. Risk Assessment**

**Identify ALL Risks:**
1. **Explicit Risks**: unfavorable terms stated
2. **Implicit Risks**: from structure or omissions
3. **Market Risks**: below/above market terms
4. **Operational Risks**: business impact
5. **Legal Risks**: enforceability issues

**F. Missing Provisions Analysis**
Compare to standard {lease_type.value} lease expectations:
- What's typically included but missing?
- What protections are absent?
- What clarifications are needed?

**3. SPECIAL INSTRUCTIONS FOR COMPLEX DOCUMENTS**

**A. Amendments:**
- Track what's being modified
- Identify base lease references
- Note cumulative changes

**B. Unclear Provisions:**
- State the ambiguity precisely
- Provide most reasonable interpretation
- Note legal risks of ambiguity
- Suggest clarifying language

**C. Cross-References:**
- Track all "as defined in Section X" references
- Flag broken references
- Build definition dictionary

**4. OUTPUT FORMAT**

Return comprehensive JSON:
```json
{{
  "document_classification": {{
    "type": "base_lease|amendment|sublease|other",
    "lease_category": "{lease_type.value}|other",
    "certainty": 0.0-1.0,
    "unusual_features": ["feature1", "feature2"]
  }},
  "extracted_terms": {{
    "parties": {{}},
    "premises": {{}},
    "financial_terms": {{}},
    "operational_terms": {{}},
    "legal_provisions": {{}}
  }},
  "financial_analysis": {{
    "calculations": [{{"metric": "", "value": "", "formula": "", "assumptions": []}}],
    "total_obligation": "",
    "effective_rate": ""
  }},
  "risk_analysis": {{
    "critical_risks": [{{"risk": "", "severity": "", "mitigation": ""}}],
    "missing_protections": [],
    "unusual_provisions": [],
    "ambiguities": []
  }},
  "relationships": {{
    "dependencies": [{{"from": "", "to": "", "type": ""}}],
    "conflicts": [],
    "modifications": []
  }},
  "completeness": {{
    "score": 0.0-1.0,
    "missing_sections": [],
    "incomplete_provisions": []
  }},
  "recommendations": []
}}
```

Provide thorough analysis befitting a senior attorney's review."""

    return system_prompt, user_prompt


def get_cross_reference_resolution_prompt(
    current_content: str,
    referenced_content: str,
    reference_type: str
) -> Tuple[str, str]:
    """
    AI-native prompt for resolving cross-references between sections.
    """
    
    system_prompt = """You are an expert legal document analyst specializing in interpreting cross-references and dependencies in commercial leases. You understand:

**Reference Types:**
- Defined terms ("Landlord" as defined in Section 1.1)
- Conditional triggers (subject to Section X)
- Procedural requirements (in accordance with Section Y)
- Incorporated provisions (terms of Exhibit A apply)
- Modified terms (except as modified by Section Z)

**Legal Interpretation Rules:**
- Later provisions control over earlier ones
- Specific provisions control over general ones
- Defined terms maintain consistent meaning
- Ambiguities construed against drafter

**Risk Factors:**
- Circular references creating uncertainty
- Conflicting provisions requiring reconciliation
- Missing referenced sections creating gaps
- Ambiguous modification language"""

    user_prompt = f"""**1. REFERENCE CONTEXT**
- Reference Type: {reference_type}
- Direction: Current section {'incorporates' if 'defined' in reference_type else 'depends on'} referenced section

**2. CURRENT SECTION CONTENT**
```
{current_content}
```

**3. REFERENCED SECTION CONTENT**
```
{referenced_content}
```

**4. ANALYSIS REQUIREMENTS**

**A. Reference Resolution:**
1. How does the referenced content modify the current section?
2. What specific terms/values are imported?
3. Are there any conflicts between sections?
4. What obligations/rights are created by the combination?

**B. Legal Interpretation:**
1. Which section controls in case of conflict?
2. Are there ambiguities in how they interact?
3. What's the business purpose of this reference?
4. How would a court likely interpret this?

**C. Risk Assessment:**
1. Does the reference create circular dependencies?
2. Are there gaps in the cross-reference?
3. Could this reference be interpreted multiple ways?
4. What protections might be lost through this structure?

**5. REQUIRED OUTPUT FORMAT**

```json
{{
  "reference_analysis": {{
    "reference_type": "{reference_type}",
    "is_valid_reference": true|false,
    "reference_purpose": "business/legal reason"
  }},
  "combined_interpretation": {{
    "merged_meaning": "complete interpretation",
    "imported_terms": {{"term": "value"}},
    "modified_obligations": ["obligation1", "obligation2"],
    "new_conditions": ["condition1", "condition2"]
  }},
  "conflicts_and_ambiguities": [
    {{
      "type": "conflict|ambiguity|gap",
      "description": "specific issue",
      "severity": "critical|high|medium|low",
      "resolution": "how to resolve"
    }}
  ],
  "legal_analysis": {{
    "controlling_provision": "which section controls",
    "interpretation_rationale": "why",
    "alternative_readings": ["alt1", "alt2"],
    "recommended_clarification": "suggested language"
  }},
  "risk_assessment": {{
    "circular_reference": true|false,
    "missing_elements": ["element1"],
    "interpretation_risks": ["risk1"],
    "confidence": 0.0-1.0
  }}
}}
```

**6. SPECIAL HANDLING INSTRUCTIONS**

**For Missing References:**
- Note exact missing reference
- Infer likely content from context
- Flag high risk
- Suggest standard provision

**For Circular References:**
- Map the circular path
- Identify breaking point
- Suggest resolution
- Flag legal uncertainty

**For Conflicting Terms:**
- State conflict precisely
- Apply legal interpretation rules
- Recommend which controls
- Suggest harmonizing language"""

    return system_prompt, user_prompt


def get_calculation_prompt(
    financial_terms: Dict[str, Any],
    lease_term_info: Dict[str, Any]
) -> Tuple[str, str]:
    """
    AI-native prompt for performing lease calculations.
    """
    
    system_prompt = """You are a real estate financial analyst specializing in lease economics. Your expertise includes:

**Financial Modeling:**
- DCF analysis and NPV calculations
- Effective rent calculations
- CAM and operating expense projections
- Percentage rent breakpoint analysis
- Escalation compounding (simple vs compound)

**Market Knowledge:**
- Typical expense ratios by property type
- Market escalation rates
- Standard CAM charges by region
- Industry financial metrics

**Accounting Standards:**
- ASC 842 lease accounting
- Straight-line rent calculations
- Present value determinations
- Lease classification tests

Always show your work, state assumptions clearly, and flag when information is insufficient for accurate calculations."""

    user_prompt = f"""**1. AVAILABLE FINANCIAL DATA**

**Financial Terms:**
```json
{financial_terms}
```

**Lease Term Information:**
```json
{lease_term_info}
```

**2. REQUIRED CALCULATIONS**

**A. Base Rent Analysis:**
1. Total base rent over initial term
2. Average annual base rent
3. Straight-line monthly rent
4. Present value at 6% discount rate

**B. Escalation Impact:**
1. Year-by-year rent with escalations
2. Total escalation amount
3. Effective escalation rate
4. Compound vs simple growth difference

**C. Total Occupancy Cost:**
1. Base rent + CAM + taxes + insurance
2. Estimated annual increases
3. Total cost over lease term
4. Cost per square foot per year

**D. Additional Calculations:**
1. Security deposit as months of rent
2. Free rent value
3. TI allowance per square foot
4. Percentage rent if sales provided
5. Break-even sales for percentage rent

**3. CALCULATION METHODOLOGY**

**For Each Calculation:**
- State the formula used
- List all assumptions
- Show step-by-step work
- Note missing data needed
- Provide confidence level

**4. REQUIRED OUTPUT FORMAT**

```json
{{
  "calculations": [
    {{
      "metric": "Total Base Rent",
      "value": 0.00,
      "formula": "sum of monthly rent * 12 * years",
      "detailed_calculation": "show work",
      "assumptions": [
        "No free rent periods",
        "Rent starts month 1"
      ],
      "missing_data": ["exact commencement date"],
      "confidence": 0.95
    }}
  ],
  "financial_summary": {{
    "total_lease_obligation": 0.00,
    "effective_annual_rent": 0.00,
    "effective_monthly_rent": 0.00,
    "cost_per_sf_per_year": 0.00,
    "npv_at_6_percent": 0.00
  }},
  "year_by_year": [
    {{
      "year": 1,
      "base_rent": 0.00,
      "cam_charges": 0.00,
      "total_occupancy": 0.00,
      "notes": "includes 2 months free"
    }}
  ],
  "key_insights": [
    "Effective rent is X% below face rent due to concessions",
    "CAM charges estimated to increase total cost by Y%",
    "Break-even for percentage rent at $Z in annual sales"
  ],
  "data_quality": {{
    "completeness": 0.0-1.0,
    "missing_critical_data": ["item1", "item2"],
    "assumptions_impact": "high|medium|low"
  }}
}}
```

**5. SPECIAL CALCULATION RULES**

**For Missing Data:**
- Use industry standards (note source)
- State assumption clearly
- Provide range if uncertain
- Flag impact on accuracy

**For Complex Structures:**
- Break into components
- Calculate each separately
- Show combined effect
- Verify reasonableness

**For Percentage Rent:**
- Natural breakpoint = Base Rent / Percentage
- Show graduated calculations
- Include exclusions impact

**6. VALIDATION CHECKS**
- Is effective rent reasonable for market?
- Do escalations compound properly?
- Are CAM estimates within normal range?
- Does total obligation make business sense?"""

    return system_prompt, user_prompt


def get_implicit_term_extraction_prompt(
    explicit_terms: Dict[str, Any],
    lease_type: LeaseType
) -> Tuple[str, str]:
    """
    AI-native prompt for finding implicit terms and obligations.
    """
    
    system_prompt = f"""You are a senior real estate attorney specializing in {lease_type.value} leases with expertise in:

**Legal Doctrines:**
- Implied covenant of good faith and fair dealing
- Quiet enjoyment and constructive eviction
- Waste and reasonable use doctrines
- Commercial frustration of purpose
- Statutory obligations by jurisdiction

**Industry Standards for {lease_type.value}:**
{"- Retail: continuous operation, percentage rent reporting, co-tenancy dependencies" if lease_type.value == "RETAIL" else ""}
{"- Office: building standard services, normal business hours, life safety compliance" if lease_type.value == "OFFICE" else ""}
{"- Industrial: environmental compliance, truck access maintenance, structural integrity" if lease_type.value == "INDUSTRIAL" else ""}

**Commercial Reasonableness:**
- What sophisticated parties typically negotiate
- Standard protections even if not stated
- Operational necessities for business viability
- Risk allocations common in the market"""

    user_prompt = f"""**1. EXPLICIT TERMS PROVIDED**

```json
{explicit_terms}
```

**2. LEASE TYPE CONTEXT**
- Property Type: {lease_type.value}
- Implied Market Standards: Apply current market norms
- Jurisdiction: Assume standard U.S. commercial law

**3. ANALYSIS REQUIREMENTS**

**A. Legal Implications - What's Automatically Implied:**

1. **Statutory Requirements**
   - ADA compliance obligations
   - Environmental law compliance
   - Building code adherence
   - Zoning compliance

2. **Common Law Doctrines**
   - Quiet enjoyment rights
   - Good faith obligations
   - Waste prevention duties
   - Reasonable use standards

3. **Industry Custom**
   - Standard service levels
   - Typical operating procedures
   - Market practice allocations
   - Customary protections

**B. Operational Necessities - What Must Exist:**

1. **For Tenant Operations**
   - Access rights (24/7 or business hours)
   - Utility availability
   - Life safety systems
   - Parking adequacy

2. **For Landlord Operations**
   - Right to maintain building
   - Access for emergencies
   - Ability to show space
   - Right to enforce rules

**C. Gap Analysis - What's Missing:**

1. **Standard Protections Not Stated**
   - Force majeure provisions
   - Condemnation procedures
   - Casualty restoration
   - Dispute resolution

2. **Clarifications Needed**
   - Measurement standards
   - Notice procedures
   - Consent standards
   - Allocation methods

**4. REQUIRED OUTPUT FORMAT**

```json
{{
  "implied_legal_obligations": [
    {{
      "obligation": "specific duty/right",
      "applies_to": "Landlord|Tenant|Both",
      "legal_basis": "statute|common law|industry custom",
      "description": "what this means practically",
      "strength": "mandatory|very likely|probable",
      "enforcement": "how this would be enforced"
    }}
  ],
  "operational_implications": [
    {{
      "necessity": "what must exist",
      "rationale": "why required",
      "typical_provision": "how usually handled",
      "risk_without": "consequence if not addressed"
    }}
  ],
  "standard_gap_analysis": {{
    "missing_critical_provisions": [
      {{
        "provision": "what's missing",
        "importance": "critical|high|medium",
        "typical_language": "standard provision",
        "risk": "specific exposure"
      }}
    ],
    "ambiguous_allocations": [
      {{
        "issue": "what's unclear",
        "market_standard": "typical allocation",
        "recommended_clarification": "suggested approach"
      }}
    ]
  }},
  "judicial_interpretation": {{
    "likely_court_implications": [
      "Court would likely imply X because Y",
      "Ambiguity about Z would be resolved by..."
    ],
    "precedent_applications": [
      "Similar to [case type] where courts held..."
    ]
  }},
  "practical_recommendations": [
    {{
      "issue": "specific gap/ambiguity",
      "recommendation": "specific action",
      "priority": "immediate|high|medium|low",
      "sample_language": "proposed provision"
    }}
  ]
}}
```

**5. SPECIAL CONSIDERATIONS**

**For Unstated Industry Norms:**
- State the norm clearly
- Explain why it's expected
- Note regional variations
- Assess enforcement likelihood

**For Conflicting Implications:**
- Identify the conflict
- State which likely prevails
- Explain reasoning
- Suggest resolution

**For High-Risk Gaps:**
- Flag immediately
- Explain exposure
- Provide standard protection
- Rate criticality

**6. CONFIDENCE SCALING**
- Mandatory by law: 0.95-1.0
- Clear industry standard: 0.8-0.9  
- Probable implication: 0.6-0.7
- Possible but uncertain: 0.4-0.5
- Speculative: 0.2-0.3"""

    return system_prompt, user_prompt


def get_fallback_extraction_prompt(text: str) -> Tuple[str, str]:
    """
    Fallback prompt for when structured extraction fails - pure AI understanding.
    """
    
    system_prompt = """You are a senior real estate attorney tasked with salvaging information from a document where normal extraction has failed. You must:

**Identify:**
- What type of document this actually is
- Why normal extraction might have failed
- What information can still be extracted

**Adapt to:**
- Non-standard formats
- Incomplete documents  
- Foreign language terms
- Technical specifications
- Mixed document types

**Extract Despite:**
- Poor document quality
- Missing sections
- Unusual structure
- Ambiguous language
- Cross-document references

Use your full legal and business judgment to extract maximum value from challenging documents."""
    
    user_prompt = f"""**1. PROBLEMATIC DOCUMENT**

The normal extraction process has failed for this document. Your task is to extract whatever information is possible using advanced interpretation.

**Document Content:**
```
{text[:5000]}{"..." if len(text) > 5000 else ""}
```

**2. DIAGNOSTIC ANALYSIS REQUIRED**

**A. Document Classification:**
1. What type of document is this?
2. Is it a complete document or fragment?
3. What's the likely purpose/context?
4. Why might extraction have failed?

**B. Information Salvage:**
1. What key business terms are present?
2. What legal relationships exist?
3. What dates/deadlines are mentioned?
4. What financial obligations are stated?
5. What conditions or triggers appear?

**C. Structural Analysis:**
1. How is the document organized?
2. What sections/components exist?
3. What's missing that would be expected?
4. Are there references to other documents?

**3. EXTRACTION STRATEGY**

**For Non-Standard Formats:**
- Identify the format type
- Extract by logical blocks
- Note format-specific issues

**For Incomplete Documents:**
- Extract what exists
- Note what's missing
- Infer document stage/status

**For Mixed Languages:**
- Identify languages used
- Extract key terms in any language
- Note translation needs

**4. REQUIRED OUTPUT FORMAT**

```json
{{
  "document_diagnosis": {{
    "document_type": "lease|amendment|letter|term sheet|other",
    "completeness": "complete|partial|fragment",
    "format_issues": ["issue1", "issue2"],
    "extraction_challenges": ["challenge1", "challenge2"]
  }},
  "extracted_information": {{
    "parties": [{{"name": "", "role": "", "entity_type": ""}}],
    "property": {{"address": "", "description": "", "size": ""}},
    "financial_terms": [{{"type": "", "amount": "", "frequency": ""}}],
    "dates": [{{"type": "", "date": "", "description": ""}}],
    "obligations": [{{"party": "", "obligation": "", "conditions": ""}}],
    "other_provisions": [{{"category": "", "content": ""}}]
  }},
  "structural_analysis": {{
    "sections_identified": ["section1", "section2"],
    "organization_pattern": "description",
    "missing_components": ["expected1", "expected2"],
    "external_references": ["doc1", "doc2"]
  }},
  "confidence_assessment": {{
    "overall_confidence": 0.0-1.0,
    "extraction_completeness": 0.0-1.0,
    "interpretation_risks": ["risk1", "risk2"]
  }},
  "recommendations": [
    {{
      "issue": "specific problem",
      "action": "recommended next step",
      "priority": "critical|high|medium|low"
    }}
  ]
}}
```

**5. FALLBACK PRINCIPLES**

1. **Extract Something**: Even partial information has value
2. **Document Problems**: Clearly note what prevented normal extraction  
3. **Suggest Solutions**: Recommend how to obtain missing information
4. **Flag Risks**: Identify legal/business risks from incomplete extraction
5. **Maintain Standards**: Apply same rigor despite document issues

**6. SPECIAL HANDLING**

**For Legal Documents:**
- Preserve exact legal language
- Note jurisdiction indicators
- Flag enforceability concerns

**For Business Terms:**
- Extract even if informal
- Note preliminary nature
- Identify open terms

**For Technical Specs:**
- Capture specifications
- Note measurement units
- Flag ambiguities

Remember: The goal is to provide maximum value despite document challenges. Extract what you can, document what you cannot, and provide actionable recommendations."""

    return system_prompt, user_prompt
