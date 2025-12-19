"""LLM client with support for Ollama, Bedrock, and OpenRouter."""

import asyncio
from typing import Optional, List, Dict, Any
from functools import lru_cache
from dataclasses import dataclass

import litellm
from diskcache import Cache

from config.settings import Settings, get_settings, LLMProvider


@dataclass
class TokenUsage:
    """Token usage statistics for a single call."""
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


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
            
        # Token usage tracking
        self.token_usage: List[TokenUsage] = []
    
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
                # Note: Cached responses don't add to token usage stats for now
                # We could store usage in cache too if needed
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
        
        # Call LLM with retry logic
        last_error = None
        for attempt in range(self.settings.llm_retries):
            try:
                response = await litellm.acompletion(
                    **kwargs,
                    timeout=self.settings.llm_timeout,
                    num_retries=0,  # We handle retries ourselves
                )
                result = response.choices[0].message.content
                
                # Track token usage
                if hasattr(response, 'usage') and response.usage:
                    self.token_usage.append(TokenUsage(
                        model=kwargs["model"],
                        prompt_tokens=response.usage.prompt_tokens,
                        completion_tokens=response.usage.completion_tokens,
                        total_tokens=response.usage.total_tokens,
                    ))
                
                # Cache result
                if use_cache and self._cache is not None:
                    self._cache.set(cache_key, result, expire=86400)  # 24 hour cache
                
                return result
                
            except (litellm.Timeout, litellm.APIConnectionError) as e:
                last_error = e
                if attempt < self.settings.llm_retries - 1:
                    wait_time = self.settings.llm_retry_delay * (attempt + 1)
                    print(f"LLM call timed out (attempt {attempt + 1}/{self.settings.llm_retries}), "
                          f"retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                continue
            except Exception as e:
                raise RuntimeError(f"LLM call failed: {e}") from e
        
        raise RuntimeError(f"LLM call failed after {self.settings.llm_retries} attempts: {last_error}") from last_error
    
    def get_usage_summary(self) -> Dict[str, Any]:
        """Get summary of token usage by model."""
        summary = {
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "by_model": {}
        }
        
        for usage in self.token_usage:
            summary["total_tokens"] += usage.total_tokens
            summary["prompt_tokens"] += usage.prompt_tokens
            summary["completion_tokens"] += usage.completion_tokens
            
            if usage.model not in summary["by_model"]:
                summary["by_model"][usage.model] = {
                    "prompt": 0,
                    "completion": 0,
                    "total": 0,
                    "calls": 0
                }
            
            model_stats = summary["by_model"][usage.model]
            model_stats["prompt"] += usage.prompt_tokens
            model_stats["completion"] += usage.completion_tokens
            model_stats["total"] += usage.total_tokens
            model_stats["calls"] += 1
            
        return summary
    
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
