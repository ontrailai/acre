#!/usr/bin/env python3
"""
Simple test to check if asyncio is working correctly in advanced_chunker
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Get API key from environment variable
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("❌ Error: OPENAI_API_KEY environment variable not set")
    sys.exit(1)

try:
    from app.core.advanced_chunker import chunk_lease
    from app.schemas import LeaseType
    print("✅ Successfully imported chunk_lease")
    
    # Test with minimal text
    test_text = "This is a test lease agreement."
    print("🧪 Testing chunk_lease function...")
    
    result = chunk_lease(test_text, LeaseType.RETAIL)
    print(f"✅ Function executed successfully! Result type: {type(result)}")
    print(f"   Number of chunks: {len(result)}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
