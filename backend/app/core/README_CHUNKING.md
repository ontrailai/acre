# Advanced Lease Chunking System

## Overview

The Advanced Lease Chunking System is a specialized module designed for precise segmentation of commercial real estate lease documents. It improves the text chunking process to produce cleaner, more semantically meaningful chunks that align better with legal clause boundaries.

## Key Features

- **Layout-Based Chunking**: Uses document structure (headings, sections, indentation) for initial boundary detection
- **Semantic Refinement**: Further refines chunks based on sentence boundaries and semantic cohesion
- **Table Detection**: Identifies and isolates tables (like rent schedules) as separate chunks
- **Clause Classification**: Automatically tags chunks with clause types (rent, maintenance, insurance, etc.)
- **Overlap Management**: Adds contextual overlap between chunks to preserve meaning
- **Comprehensive Metadata**: Provides detailed traceability (page numbers, character positions, parent headings)

## Integration with Existing Pipeline

The advanced chunker integrates with the existing Lease Logik pipeline:

```
PDF Upload → OCR → Advanced Chunking → GPT Processing → Summary Generation
```

The system maintains backward compatibility with the existing `segment_lease` interface, with the legacy segmentation method available as a fallback if needed.

## Benefits

1. **Reduced Hallucination**: By aligning chunk boundaries with logical clauses, we reduce GPT's tendency to hallucinate or blend clauses
2. **Improved Traceability**: Enhanced metadata allows better source attribution in the final summary
3. **Better Table Handling**: Tables are processed separately with appropriate context
4. **Smarter Classification**: Chunks are pre-classified, improving prompt selection
5. **Fallback Safety**: The system gracefully degrades to legacy chunking if issues occur

## Implementation Details

### Main Components

- **`advanced_chunker.py`**: Core chunking implementation with the `AdvancedChunker` class
- **Modified `segmenter.py`**: Updated to use advanced chunking while maintaining the same interface
- **`test_chunker.py`**: Test script for validating the chunking system

### Chunking Process

1. **Layout Analysis**: Identify section boundaries using headers, numbering, and indentation
2. **Table Detection**: Find and extract tables based on formatting and content patterns
3. **Semantic Refinement**: Split large blocks while preserving semantic meaning
4. **Classification**: Apply rule-based classification to identify clause types
5. **Enrichment**: Add metadata for traceability and downstream processing

## Extensibility

The system is designed to be extended in several ways:

- Additional clause type definitions can be added for specialized lease types
- Table detection patterns can be enhanced for different table formats
- Classification rules can be refined based on observed performance
- Token estimation can be improved with more sophisticated methods

## Usage

The system is designed to be a drop-in replacement for the existing segmentation system. No changes are needed to the API endpoints or other parts of the codebase.

```python
from app.core.segmenter import segment_lease
from app.schemas import LeaseType

# API usage remains the same
segments = segment_lease(text_content, LeaseType.RETAIL)
```

## Testing

A test script is included in `tests/test_chunker.py` which demonstrates the advanced chunking on a sample lease. Run this script to see the chunking in action and analyze the results.

```bash
cd backend
python -m tests.test_chunker
```

## Monitoring and Debugging

The system includes extensive logging and debugging features:

- Debug files are saved to `app/storage/debug/advanced_chunker/`
- Each chunking stage (layout blocks, tables, semantic chunks) is saved separately
- Processing logs track key decisions and metrics

## Future Enhancements

Potential areas for future improvement:

1. **Machine learning-based clause classification**: Replace rule-based classification with a trained model
2. **Enhanced table structure extraction**: Extract structured data from tables
3. **Embedding-based semantic boundaries**: Use text embeddings to find natural semantic boundaries
4. **Advanced table detection**: Improve identification of complex table structures
5. **Token counting improvements**: Use tokenizer-specific implementations for more accurate estimates
