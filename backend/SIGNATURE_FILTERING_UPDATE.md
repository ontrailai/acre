# Signature/Certificate Section Filtering Update

## Changes Made

### 1. **Updated `gpt_extract.py`**
- Added filtering in `_extract_clauses_flat()` to skip segments with signature/certificate content
- Checks both section names and content for signature-related keywords
- Skip keywords include: "signature", "certificate", "acknowledgment", "notary", "witness", "executed", "signed", "seal", "attestation", "certification", "accuracy", "tenant signature", "landlord signature"
- Also filters out clauses during GPT response processing

### 2. **Updated `ai_native_extractor.py`**
- Added filtering in `_create_intelligent_chunks()` to skip chunks containing signature/certificate content
- Prevents signature sections from being processed by the AI-native extraction system

## Behavior

The system will now:
1. **Skip entire segments** that appear to be signature or certificate sections
2. **Filter out clauses** if GPT somehow extracts signature-related content
3. **Log all skipped sections** for debugging purposes

## Keywords Filtered

- signature
- certificate
- acknowledgment
- notary
- witness
- executed
- signed
- seal
- attestation
- certification
- accuracy
- tenant signature
- landlord signature
- certificate of accuracy

## Impact

This should prevent the system from getting stuck processing repetitive signature pages and certificate sections, while still extracting all meaningful lease content.

The extraction will focus on actual lease clauses like:
- Rent and payment terms
- Security deposits
- Use restrictions
- Maintenance responsibilities
- Insurance requirements
- Default provisions
- etc.

## Logging

All skipped sections are logged with messages like:
- "Skipping signature/certificate section: [section_name]"
- "Skipping section with signature content: [section_name]"
- "Skipping [clause_type] clause from GPT response"

This allows you to verify what's being filtered out if needed.
