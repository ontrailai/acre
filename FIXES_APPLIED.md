# Lease Logik System Fixes

## Issues Fixed

### 1. DateTimeExtractor AttributeError
**Problem**: The system was trying to call `extract_base_rent()` on the DateTimeExtractor class, which doesn't have this method.

**Fix**: Modified `enhanced_gpt_extract.py` in the `_process_segment_production` method to:
- Check the segment type first
- Call the appropriate extraction method based on the extractor type
- Added proper error handling for specialized extractors

### 2. Low Clause Extraction Count (Only 3 clauses from 36-page lease)
**Problem**: The system was only extracting 3 clauses from a residential lease because:
- Pattern matching was optimized for commercial leases
- Residential leases use different terminology (e.g., multiple tenants with "and" between names)
- The system was falling back to simplified extraction too early

**Fixes Applied**:

1. **Created `residential_patterns.py`**: A new module specifically for residential lease patterns that handles:
   - Multiple tenant names (e.g., "Deborah Hample and Riley Pasha (together and separately, Tenant)")
   - Residential-specific landlord patterns
   - Residential address formats
   - Term date patterns common in residential leases
   - Security deposit and monthly rent patterns

2. **Updated `gpt_extract_simple.py`** to:
   - Import and use residential patterns first
   - Better handle pattern extraction results
   - Improved GPT prompting for residential leases

3. **Created `pattern_converter.py`**: A helper module to convert extracted pattern data into proper ClauseExtraction format

## Files Modified/Created

1. `/Users/ryanwatson/Desktop/acre/backend/app/core/enhanced_gpt_extract.py` - Fixed the specialized extractor method calls
2. `/Users/ryanwatson/Desktop/acre/backend/app/core/residential_patterns.py` - NEW: Residential lease pattern matching
3. `/Users/ryanwatson/Desktop/acre/backend/app/core/pattern_converter.py` - NEW: Pattern data to clause converter
4. `/Users/ryanwatson/Desktop/acre/backend/app/core/gpt_extract_simple.py` - Updated to use residential patterns

## How to Test

1. Run the system again with the residential lease
2. You should now see more extracted clauses including:
   - Landlord: Jeffrey Altman
   - Tenant: Deborah Hample and Riley Pasha
   - Address: 1818 McKee St San Diego, CA 92110
   - Term dates: January 31, 2025 to January 31, 2026
   - Monthly rent: $3,650.00
   - Security deposit: $4,650.00
   - Permitted use: residential purposes only

## Additional Recommendations

1. Consider adding more lease type detection to automatically switch between commercial and residential patterns
2. Add unit tests for the new pattern matching functions
3. Consider training a separate model or fine-tuning for residential leases
4. Add validation to ensure critical fields are extracted before considering extraction complete
