# AI-Native Extraction - Maximum Data Output Configuration

## Changes Made to Get More Data

### 1. **Increased Chunk Sizes**
- Target chunk size: 2,500 → 5,000 characters
- Maximum chunk size: 3,500 → 10,000 characters
- **Result**: Fewer but more context-rich chunks (5 chunks instead of 10)

### 2. **Removed Truncation**
- Previously: Chunks truncated to 3,000 characters
- Now: Full chunks sent to GPT-4 (up to 10KB each)
- **Result**: GPT-4 sees complete context

### 3. **Extended Timeouts**
- GPT call timeout: 30s → 90s
- API timeout: 20s → 60s
- **Result**: More time for processing larger chunks

### 4. **Enhanced Extraction Prompt**
- Now requests EVERYTHING from each chunk:
  - All monetary amounts
  - All dates
  - All parties/entities
  - All obligations
  - All conditions
  - Comprehensive summaries
- **Result**: Much more detailed extraction

### 5. **Increased Parallelism**
- Semaphore limit: 5 → 10 concurrent requests
- **Result**: Faster processing of chunks

### 6. **Richer Output Format**
- Each extracted item now includes:
  - Field name and value
  - Exact source text quote
  - Additional context
  - Lists of all amounts, dates, parties, etc.
- **Result**: Complete data visibility

## What This Achieves

With these changes, the AI-native extraction will:
1. Process larger chunks with full context
2. Extract comprehensive data from each chunk
3. Have enough time to process without timeouts
4. Return structured data with all lease details

The system will now extract and return ALL lease data it finds, not just key terms.
