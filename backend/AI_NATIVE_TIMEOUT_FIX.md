# AI-Native Extraction Timeout Fix

## Problem
The AI-native extraction was timing out when processing large documents (40,022 characters) because it was trying to analyze the entire document in a single GPT call during Phase 1.

## Solutions Implemented

### 1. **Optimized Document Structure Analysis**
- **Sampling Approach**: For documents larger than 10,000 characters, we now sample from different parts:
  - Beginning (500 chars)
  - 1/3 point (500 chars)
  - 2/3 point (500 chars)
  - End (500 chars)
- **Shorter Timeout**: Structure analysis now has a 15-second timeout
- **Fallback Structure**: If timeout occurs, uses a default structure

### 2. **Smart Chunking Strategy**
- **Fast Paragraph Chunking**: For documents > 20,000 chars, uses efficient paragraph-based chunking
- **Chunk Size Limits**: 
  - Target size: 2,500 characters
  - Maximum size: 3,500 characters
- **Automatic Fallback**: If AI chunking fails or times out, falls back to paragraph chunking

### 3. **Parallel Processing**
- **Concurrent Extraction**: Processes up to 5 chunks simultaneously using asyncio semaphore
- **Error Isolation**: If one chunk fails, others continue processing
- **Progressive Loading**: Results are processed as they complete

### 4. **Optimized Prompts**
- **Reduced Prompt Size**: Simplified extraction prompts to focus on key information
- **Chunk Truncation**: Limits chunk content to 3,000 characters in prompts
- **Concise Responses**: Requests only essential fields to reduce response size

### 5. **Adaptive Processing**
- **Large Document Handling**: 
  - Skips additional passes for documents with > 20 chunks
  - Limits context enhancement to documents with ≤ 10 chunks
- **Timeout Management**: Each phase has its own timeout limits

## Performance Improvements
- Document structure analysis: 30s → 15s timeout
- Chunking: Can timeout gracefully and use fallback
- Extraction: Parallel processing reduces total time
- Overall: 40KB documents should now process within 60-90 seconds

## Key Changes
1. Added `_fast_paragraph_chunking()` method for efficient chunking
2. Modified `_understand_document_structure()` to use sampling
3. Updated `_create_intelligent_chunks()` with fallback logic
4. Parallelized `_multi_pass_extraction()` with semaphore
5. Simplified extraction prompts to reduce token usage
6. Added configurable timeouts to `_call_gpt()`

## Usage
The AI-native extraction will now automatically adapt to document size:
- Small documents (< 10KB): Full AI analysis
- Medium documents (10-20KB): Sampled analysis with AI chunking
- Large documents (> 20KB): Fast paragraph chunking with parallel extraction

The system gracefully degrades functionality for larger documents while maintaining extraction quality.
