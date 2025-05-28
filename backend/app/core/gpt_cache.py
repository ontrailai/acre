"""
Simple in-memory cache for GPT responses to speed up repeated processing
"""

import hashlib
import json
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
import asyncio

class GPTResponseCache:
    """In-memory cache for GPT responses"""
    
    def __init__(self, ttl_minutes: int = 60):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = timedelta(minutes=ttl_minutes)
        self._lock = asyncio.Lock()
    
    def _generate_key(self, prompt: str) -> str:
        """Generate a cache key from prompt"""
        return hashlib.md5(prompt.encode()).hexdigest()
    
    async def get(self, prompt: str) -> Optional[str]:
        """Get cached response if available and not expired"""
        async with self._lock:
            key = self._generate_key(prompt)
            
            if key in self.cache:
                entry = self.cache[key]
                if datetime.now() < entry['expires_at']:
                    return entry['response']
                else:
                    # Expired, remove it
                    del self.cache[key]
            
            return None
    
    async def set(self, prompt: str, response: str):
        """Cache a response"""
        async with self._lock:
            key = self._generate_key(prompt)
            self.cache[key] = {
                'response': response,
                'expires_at': datetime.now() + self.ttl,
                'created_at': datetime.now()
            }
    
    async def clear_expired(self):
        """Remove expired entries"""
        async with self._lock:
            now = datetime.now()
            expired_keys = [
                key for key, entry in self.cache.items()
                if now >= entry['expires_at']
            ]
            for key in expired_keys:
                del self.cache[key]
    
    def stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        return {
            'total_entries': len(self.cache),
            'size_bytes': sum(
                len(entry['response']) 
                for entry in self.cache.values()
            )
        }

# Global cache instance
gpt_cache = GPTResponseCache(ttl_minutes=120)  # 2 hour TTL
