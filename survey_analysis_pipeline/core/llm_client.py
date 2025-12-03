"""LLM client with support for Ollama, Bedrock, and OpenRouter."""

import asyncio
from typing import Optional, List, Dict, Any
from functools import lru_cache

import litellm
from diskcache import Cache

from config.settings import Settings, get_settings, LLMProvider


class LLMClient:
    """Unified LLM client supporting multiple providers."""
    
    def __init__(self, settings: Optional[Settings] = None):
        """Initialize LLM client.
        
        Args:
            settings: Application settings. Uses default if not provided.
        """
        self.settings = settings or get_settings()
        self._setup_provider()
        
        # Setup cache if enabled
        self._cache: Optional[Cache] = None
        if self.settings.cache_enabled:
            cache_dir = self.settings.cache_dir
            cache_dir.mkdir(parents=True, exist_ok=True)
            self._cache = Cache(str(cache_dir / "llm_cache"))
    
    def _setup_provider(self) -> None:
        """Setup LLM provider configuration."""
        provider = self.settings.llm_provider
        
        if provider == LLMProvider.OLLAMA:
            # Ollama doesn't need special setup with litellm
            self.model = f"ollama/{self.settings.ollama_model}"
            self.api_base = self.settings.ollama_base_url
            
        elif provider == LLMProvider.BEDROCK:
            # Setup AWS credentials for Bedrock
            self.model = f"bedrock/{self.settings.bedrock_model_id}"
            self.api_base = None
            # litellm will use boto3 credentials automatically
            
        elif provider == LLMProvider.OPENROUTER:
            self.model = f"openrouter/{self.settings.openrouter_model}"
            self.api_base = self.settings.openrouter_base_url
            litellm.api_key = self.settings.openrouter_api_key
        
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    def _get_cache_key(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Generate cache key from request parameters."""
        import hashlib
        import json
        
        cache_data = {
            "model": self.model,
            "messages": messages,
            "kwargs": {k: v for k, v in kwargs.items() if k not in ["stream"]}
        }
        return hashlib.sha256(json.dumps(cache_data, sort_keys=True).encode()).hexdigest()
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        use_cache: bool = True,
    ) -> str:
        """Generate text using the configured LLM.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Override temperature setting
            max_tokens: Override max tokens setting
            use_cache: Whether to use response cache
            
        Returns:
            Generated text response
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        return await self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            use_cache=use_cache,
        )
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        use_cache: bool = True,
    ) -> str:
        """Chat completion with message history.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Override temperature setting
            max_tokens: Override max tokens setting
            use_cache: Whether to use response cache
            
        Returns:
            Assistant's response text
        """
        temp = temperature if temperature is not None else self.settings.temperature
        tokens = max_tokens if max_tokens is not None else self.settings.max_tokens
        
        # Check cache
        if use_cache and self._cache is not None:
            cache_key = self._get_cache_key(messages, temperature=temp, max_tokens=tokens)
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached
        
        # Prepare kwargs
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temp,
            "max_tokens": tokens,
        }
        
        # Add api_base for Ollama and OpenRouter
        if self.api_base:
            kwargs["api_base"] = self.api_base
        
        # Add AWS region for Bedrock
        if self.settings.llm_provider == LLMProvider.BEDROCK:
            kwargs["aws_region_name"] = self.settings.aws_region
        
        # Call LLM
        try:
            response = await litellm.acompletion(**kwargs)
            result = response.choices[0].message.content
            
            # Cache result
            if use_cache and self._cache is not None:
                self._cache.set(cache_key, result, expire=86400)  # 24 hour cache
            
            return result
            
        except Exception as e:
            raise RuntimeError(f"LLM call failed: {e}") from e
    
    def generate_sync(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        use_cache: bool = True,
    ) -> str:
        """Synchronous version of generate."""
        return asyncio.run(self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            use_cache=use_cache,
        ))
    
    def chat_sync(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        use_cache: bool = True,
    ) -> str:
        """Synchronous version of chat."""
        return asyncio.run(self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            use_cache=use_cache,
        ))
    
    def close(self) -> None:
        """Close resources."""
        if self._cache is not None:
            self._cache.close()


@lru_cache()
def get_llm_client() -> LLMClient:
    """Get cached LLM client instance."""
    return LLMClient()

