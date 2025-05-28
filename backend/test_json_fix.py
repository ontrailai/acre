#!/usr/bin/env python3
"""
Quick test script to verify the JSON format fix
"""

import asyncio
import os
from app.schemas import LeaseType
from app.core.gpt_extract import call_openai_api

async def test_json_fix():
    """Test that the JSON format fix works"""
    
    # Test prompts without "json" word
    system_prompt = "You are an expert lease analyst. Extract information from the text."
    user_prompt = "Extract the tenant name from this text: The tenant is ACME Corp."
    
    print("Testing GPT call with prompts that don't contain 'json'...")
    
    try:
        response = await call_openai_api(system_prompt, user_prompt)
        print(f"Success! Response: {response[:100]}...")
    except Exception as e:
        print(f"Error: {e}")
        
    # Test prompts with "json" word
    system_prompt = "You are an expert lease analyst. Return JSON responses."
    user_prompt = "Extract the tenant name from this text: The tenant is ACME Corp. Return as JSON."
    
    print("\nTesting GPT call with prompts that contain 'json'...")
    
    try:
        response = await call_openai_api(system_prompt, user_prompt)
        print(f"Success! Response: {response[:100]}...")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_json_fix())
