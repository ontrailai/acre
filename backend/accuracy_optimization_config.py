"""
Lease Logik Accuracy Optimization Configuration
==============================================

This file contains all settings optimized for maximum extraction accuracy using GPT-4.
Apply these settings across the system for best results.
"""

# Model Configuration - Use GPT-4 exclusively
MODEL_CONFIG = {
    "extraction": {
        "model": "gpt-4-turbo-preview",
        "temperature": 0.1,  # Low temperature for consistency
        "max_tokens": 8000   # Maximum tokens for comprehensive extraction
    },
    "classification": {
        "model": "gpt-4-turbo-preview",  # GPT-4 for all tasks
        "temperature": 0.1,
        "max_tokens": 2000
    },
    "summary": {
        "model": "gpt-4-turbo-preview",
        "temperature": 0.2,
        "max_tokens": 4000
    },
    "risk_analysis": {
        "model": "gpt-4-turbo-preview",
        "temperature": 0.1,
        "max_tokens": 4000
    },
    "ai_native": {
        "model": "gpt-4-turbo-preview",
        "temperature": 0.1,
        "max_tokens": 8000
    }
}

# Optimization Flags - Accuracy focused
OPTIMIZATION_FLAGS = {
    "use_caching": True,
    "batch_small_requests": False,  # Process individually for accuracy
    "prefer_fast_models_for_classification": False,  # Always use GPT-4
    "aggressive_chunking": False,  # Preserve semantic boundaries
    "parallel_extraction": True,
    "enable_ai_native": True,  # Use AI-native extraction
    "enable_multi_pass": True,  # Multiple passes for completeness
    "enable_cross_reference": True,  # Cross-reference between sections
    "enable_risk_analysis": True,  # Deep risk analysis
    "enable_completeness_check": True,  # Verify all clauses extracted
    "chunk_overlap": 200,  # Token overlap between chunks
    "min_confidence_threshold": 0.7,  # Minimum confidence
    "use_structured_prompts": True,  # Structured prompt templates
    "enable_table_extraction": True,  # Extract tables separately
    "enable_clause_validation": True,  # Validate extracted clauses
    "max_chunk_tokens": 2000,  # Optimal chunk size for detailed analysis
    "enable_specialized_extractors": True,  # Use specialized AI extractors
    "enable_document_graph": True,  # Build document relationship graph
    "enable_embedding_similarity": True,  # Find similar/duplicate clauses
    "enable_audit_trail": True  # Complete audit trail
}

# Chunking Configuration - Preserve context
CHUNKING_CONFIG = {
    "method": "ai_native",  # Use AI-native chunking
    "preserve_hierarchy": True,
    "max_chunk_size": 2000,  # Tokens
    "min_chunk_size": 200,   # Tokens
    "overlap_tokens": 200,
    "group_similar": False,  # Don't group - process individually
    "semantic_boundaries": True,
    "preserve_tables": True,
    "preserve_lists": True
}

# Extraction Configuration
EXTRACTION_CONFIG = {
    "parallel_segments": 8,  # Process 8 segments in parallel
    "timeout_per_segment": 25,  # 25 seconds per segment
    "retry_attempts": 2,
    "use_specialized_extractors": True,
    "cross_reference_sections": True,
    "extract_implicit_info": True,
    "validate_relationships": True,
    "confidence_threshold": 0.7
}

# Prompt Engineering Best Practices
PROMPT_CONFIG = {
    "include_reasoning": True,  # Ask GPT to explain its reasoning
    "request_confidence": True,  # Always request confidence scores
    "structured_output": True,   # Request JSON output
    "explicit_instructions": True,
    "context_window": 2000,     # Tokens of context
    "few_shot_examples": False,  # Don't use examples - let GPT think
    "chain_of_thought": True    # Enable step-by-step reasoning
}

# Rate Limiting - Optimized for Tier 3
RATE_LIMIT_CONFIG = {
    "max_retries": 3,
    "base_delay": 0.5,
    "max_concurrent_requests": 10,
    "tokens_per_minute": 150000,  # Tier 3 limit
    "requests_per_minute": 500,    # Tier 3 limit
    "use_exponential_backoff": True
}

# Quality Assurance Settings
QA_CONFIG = {
    "enable_validation": True,
    "check_completeness": True,
    "verify_calculations": True,
    "cross_validate_dates": True,
    "flag_ambiguities": True,
    "require_source_text": True,
    "track_confidence": True,
    "log_reasoning": True
}

# Debug and Monitoring
DEBUG_CONFIG = {
    "save_all_prompts": True,
    "save_all_responses": True,
    "track_token_usage": True,
    "measure_latency": True,
    "log_extraction_decisions": True,
    "export_audit_trail": True,
    "verbose_logging": True
}

def get_gpt_config_for_task(task_type: str) -> dict:
    """Get GPT configuration for a specific task type"""
    base_config = MODEL_CONFIG.get(task_type, MODEL_CONFIG["extraction"])
    
    # Always use GPT-4 for accuracy
    base_config["model"] = "gpt-4-turbo-preview"
    
    # Adjust temperature based on task
    if task_type in ["classification", "extraction", "risk_analysis"]:
        base_config["temperature"] = 0.1  # Very low for consistency
    elif task_type == "summary":
        base_config["temperature"] = 0.2  # Slightly higher for natural language
        
    return base_config

def get_optimal_chunk_size(content_length: int) -> int:
    """Determine optimal chunk size based on content"""
    if content_length < 1000:
        return content_length  # Don't chunk small content
    elif content_length < 5000:
        return 1500  # Medium chunks
    else:
        return 2000  # Larger chunks for long documents
        
def should_use_specialized_extractor(section_content: str, section_name: str) -> bool:
    """Determine if specialized extractor should be used"""
    # Always try specialized extractors for better accuracy
    keywords = {
        "financial": ["rent", "payment", "fee", "charge", "cost"],
        "datetime": ["date", "term", "deadline", "notice", "commencement"],
        "conditional": ["if", "condition", "contingent", "subject to", "provided"],
        "rights": ["option", "right", "renewal", "expansion", "termination"]
    }
    
    section_lower = section_name.lower()
    content_lower = section_content.lower()[:500]  # Check first 500 chars
    
    for extractor_type, terms in keywords.items():
        if any(term in section_lower or term in content_lower for term in terms):
            return True
            
    return False

# Accuracy-Optimized Prompt Templates
ACCURACY_PROMPTS = {
    "extraction_system": """You are an expert commercial lease analyst with deep legal knowledge.
Your task is to extract information with maximum accuracy and completeness.

Key principles:
1. Extract EVERYTHING - both explicit and implicit information
2. Identify risks even if subtle or implied
3. Note ambiguities and missing information
4. Provide confidence scores for each extraction
5. Explain your reasoning for complex extractions
6. Flag any calculations needed
7. Identify cross-references to other sections

Do not use pattern matching. Use deep understanding of legal language and commercial terms.""",

    "validation_prompt": """Review this extraction for accuracy and completeness.
Check for:
1. Missing critical information
2. Logical inconsistencies
3. Calculation errors
4. Date/timeline conflicts
5. Ambiguous terms needing clarification
6. Unusual or concerning provisions

Provide specific recommendations for improvement."""
}

print("Accuracy optimization configuration loaded successfully!")
print("Key settings:")
print(f"- Model: {MODEL_CONFIG['extraction']['model']}")
print(f"- Max tokens per request: {MODEL_CONFIG['extraction']['max_tokens']}")
print(f"- Parallel segments: {EXTRACTION_CONFIG['parallel_segments']}")
print(f"- AI-native extraction: {OPTIMIZATION_FLAGS['enable_ai_native']}")
print(f"- Multi-pass extraction: {OPTIMIZATION_FLAGS['enable_multi_pass']}")
print(f"- Specialized extractors: {OPTIMIZATION_FLAGS['enable_specialized_extractors']}")
