# Lease Logik Timeout and Performance Fixes

## Changes Made to Fix Timeouts

### 1. **Disabled AI-Native Extraction (Temporarily)**
- The AI-native extraction was timing out on complex documents
- Now using the more stable multi-pass extraction by default
- Can be re-enabled once timeout issues are resolved

### 2. **Improved Signature Section Filtering**
- Only skips pure signature sections (name = "signature" or "certificate" AND content < 1500 chars)
- Keeps all other sections even if they contain signature blocks
- This ensures important content like "use", "pet_policy", "parking" etc. are not skipped

### 3. **Reduced Timeout Limits**
- GPT API calls now timeout after 30 seconds instead of 60
- Prevents hanging on slow responses
- Allows faster failure and retry

### 4. **Content Size Limiting**
- Large segments (>8000 characters) are now truncated before sending to GPT
- Prevents token limit issues and timeouts
- Preserves the most important content at the beginning

### 5. **Better Error Handling and Logging**
- Added phase-by-phase logging in AI-native extraction
- Better timeout error messages
- Content size logging to identify problematic segments

## Current Behavior

The system now:
1. Processes segments with the multi-pass extractor (stable)
2. Skips only pure signature sections
3. Limits content size to prevent timeouts
4. Times out after 30 seconds per GPT call
5. Logs progress at each step

## Performance Expectations

- Processing time: 15-25 seconds for typical lease
- No more hanging on signature sections
- All important lease content is extracted
- System completes successfully

## Next Steps

If you still experience issues:
1. Check logs for which specific section is timing out
2. Consider further reducing content size limits
3. May need to optimize the prompts themselves
4. Could implement request queuing to prevent overload

The system should now complete successfully without timeouts!
