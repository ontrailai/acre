"""
Model configuration for Lease Logik
"""

# Model selection - Full GPT-4 for maximum accuracy
MODEL_CONFIG = {
    # For complex clause extraction and analysis
    "extraction": {
        "model": "gpt-4-turbo-preview",
        "temperature": 0.1,  # Low temperature for consistency
        "max_tokens": 8000   # Increased for comprehensive extraction
    },
    
    # Classification also uses GPT-4 for accuracy
    "classification": {
        "model": "gpt-4-turbo-preview",  # Full GPT-4 for accuracy
        "temperature": 0.1,
        "max_tokens": 2000  # Increased for better classification
    },
    
    # For summary generation
    "summary": {
        "model": "gpt-4-turbo-preview",
        "temperature": 0.2,  # Slightly lower for more consistent summaries
        "max_tokens": 4000  # Increased for detailed summaries
    },
    
    # Risk analysis with GPT-4
    "risk_analysis": {
        "model": "gpt-4-turbo-preview",
        "temperature": 0.1,
        "max_tokens": 4000
    },
    
    # AI-native extraction with GPT-4
    "ai_native": {
        "model": "gpt-4-turbo-preview",
        "temperature": 0.1,
        "max_tokens": 8000
    }
}

# Rate limit handling - Tier 3 limits
RATE_LIMIT_CONFIG = {
    "max_retries": 3,
    "base_delay": 0.5,  # seconds
    "max_concurrent_requests": 10,
    "tokens_per_minute": 150000,  # Tier 3 limit
    "requests_per_minute": 500     # Tier 3 limit
}

# Performance optimization flags - Accuracy focused
OPTIMIZATION_FLAGS = {
    "use_caching": True,
    "batch_small_requests": False,  # Process each request individually for accuracy
    "prefer_fast_models_for_classification": False,  # Always use GPT-4
    "aggressive_chunking": False,  # Keep semantic boundaries intact
    "parallel_extraction": True,
    "enable_ai_native": True,  # Use AI-native extraction for maximum intelligence
    "enable_multi_pass": True,  # Multiple passes for completeness
    "enable_cross_reference": True,  # Cross-reference between sections
    "enable_risk_analysis": True,  # Deep risk analysis
    "enable_completeness_check": True,  # Verify all clauses extracted
    "chunk_overlap": 200,  # Token overlap between chunks for context
    "min_confidence_threshold": 0.7,  # Minimum confidence for extraction
    "use_structured_prompts": True,  # Use structured prompt templates
    "enable_table_extraction": True,  # Extract tables separately
    "enable_clause_validation": True  # Validate extracted clauses
}
