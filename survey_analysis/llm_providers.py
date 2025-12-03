"""
Unified LLM provider interface for Claude, Gemini, and Ollama.

This module provides a consistent interface for interacting with multiple
LLM providers (Claude Sonnet 4.5, Gemini 3 Pro, and Ollama local models).
"""

import time
import requests
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import anthropic
import google.generativeai as genai

from config import (
    ANTHROPIC_API_KEY,
    GOOGLE_API_KEY,
    CLAUDE_MODEL,
    GEMINI_MODEL,
    MAX_RETRIES,
    RETRY_DELAY,
    REQUEST_TIMEOUT,
)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.request_count = 0
        self.total_tokens = 0
    
    @abstractmethod
    def generate(
        self,
        prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Generate text from the LLM.
        
        Args:
            prompt: The user prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            system_prompt: Optional system prompt
        
        Returns:
            Generated text response
        """
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Get the name of this provider."""
        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get usage statistics."""
        return {
            'provider': self.get_name(),
            'model': self.model_name,
            'request_count': self.request_count,
            'total_tokens': self.total_tokens
        }


class ClaudeProvider(LLMProvider):
    """Claude Sonnet 4.5 provider."""
    
    def __init__(self):
        super().__init__(CLAUDE_MODEL)
        
        if not ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
        
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    def generate(
        self,
        prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None
    ) -> str:
        """Generate text using Claude."""
        for attempt in range(MAX_RETRIES):
            try:
                messages = [{"role": "user", "content": prompt}]
                
                kwargs = {
                    "model": self.model_name,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "messages": messages,
                }
                
                if system_prompt:
                    kwargs["system"] = system_prompt
                
                response = self.client.messages.create(**kwargs)
                
                self.request_count += 1
                self.total_tokens += response.usage.input_tokens + response.usage.output_tokens
                
                return response.content[0].text
            
            except anthropic.RateLimitError as e:
                if attempt < MAX_RETRIES - 1:
                    print(f"⚠️  Rate limit hit, waiting {RETRY_DELAY}s...")
                    time.sleep(RETRY_DELAY)
                else:
                    raise
            
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    print(f"⚠️  Error: {e}, retrying...")
                    time.sleep(RETRY_DELAY)
                else:
                    raise
    
    def get_name(self) -> str:
        return "claude"


class GeminiProvider(LLMProvider):
    """Gemini 3 Pro provider."""
    
    def __init__(self):
        super().__init__(GEMINI_MODEL)
        
        if not GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY environment variable is not set")
        
        genai.configure(api_key=GOOGLE_API_KEY)
        self.model = genai.GenerativeModel(self.model_name)
    
    def generate(
        self,
        prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None
    ) -> str:
        """Generate text using Gemini."""
        # Combine system prompt and user prompt for Gemini
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        for attempt in range(MAX_RETRIES):
            try:
                generation_config = genai.types.GenerationConfig(
                    max_output_tokens=max_tokens,
                    temperature=temperature,
                )
                
                response = self.model.generate_content(
                    full_prompt,
                    generation_config=generation_config
                )
                
                self.request_count += 1
                
                # Gemini token counting
                if hasattr(response, 'usage_metadata'):
                    self.total_tokens += (
                        response.usage_metadata.prompt_token_count +
                        response.usage_metadata.candidates_token_count
                    )
                
                return response.text
            
            except Exception as e:
                if "429" in str(e) or "quota" in str(e).lower():
                    if attempt < MAX_RETRIES - 1:
                        print(f"⚠️  Rate limit hit, waiting {RETRY_DELAY}s...")
                        time.sleep(RETRY_DELAY)
                    else:
                        raise
                elif attempt < MAX_RETRIES - 1:
                    print(f"⚠️  Error: {e}, retrying...")
                    time.sleep(RETRY_DELAY)
                else:
                    raise
    
    def get_name(self) -> str:
        return "gemini"


class OllamaProvider(LLMProvider):
    """Ollama local LLM provider."""
    
    def __init__(self, model_name: str = "gpt-oss20b", base_url: str = "http://localhost:11434"):
        super().__init__(model_name)
        self.base_url = base_url
        self.session = requests.Session()
        
        # Check if Ollama server is running
        try:
            response = self.session.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise ConnectionError(
                f"Cannot connect to Ollama server at {self.base_url}. "
                f"Please ensure Ollama is running: 'ollama serve'"
            ) from e
    
    def generate(
        self,
        prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None
    ) -> str:
        """Generate text using Ollama."""
        # Combine system prompt and user prompt
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        for attempt in range(MAX_RETRIES):
            try:
                payload = {
                    "model": self.model_name,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens,
                    }
                }
                
                response = self.session.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    timeout=REQUEST_TIMEOUT
                )
                response.raise_for_status()
                
                result = response.json()
                self.request_count += 1
                
                # Ollama provides token counts in the response
                if 'eval_count' in result:
                    self.total_tokens += result.get('prompt_eval_count', 0) + result.get('eval_count', 0)
                
                return result['response']
            
            except requests.exceptions.Timeout:
                if attempt < MAX_RETRIES - 1:
                    print(f"⚠️  Request timeout, retrying...")
                    time.sleep(RETRY_DELAY)
                else:
                    raise TimeoutError(f"Ollama request timed out after {REQUEST_TIMEOUT}s")
            
            except requests.exceptions.RequestException as e:
                if attempt < MAX_RETRIES - 1:
                    print(f"⚠️  Error: {e}, retrying...")
                    time.sleep(RETRY_DELAY)
                else:
                    raise
            
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    print(f"⚠️  Error: {e}, retrying...")
                    time.sleep(RETRY_DELAY)
                else:
                    raise
    
    def get_name(self) -> str:
        return "ollama"


def get_provider(provider_name: str, model_name: Optional[str] = None) -> LLMProvider:
    """
    Factory function to get an LLM provider by name.
    
    Args:
        provider_name: Name of provider ("claude", "gemini", or "ollama")
        model_name: Optional model name (used for Ollama)
    
    Returns:
        LLMProvider instance
    """
    provider_name = provider_name.lower()
    
    if provider_name == "claude":
        return ClaudeProvider()
    elif provider_name == "gemini":
        return GeminiProvider()
    elif provider_name == "ollama":
        return OllamaProvider(model_name=model_name or "gpt-oss20b")
    else:
        raise ValueError(f"Unknown provider: {provider_name}. Use 'claude', 'gemini', or 'ollama'")


def test_providers():
    """Test all providers with a simple prompt."""
    test_prompt = "こんにちは！あなたの名前は何ですか？簡単に自己紹介してください。"
    
    print("\n" + "="*70)
    print("TESTING LLM PROVIDERS")
    print("="*70 + "\n")
    
    for provider_name in ["claude", "gemini", "ollama"]:
        print(f"Testing {provider_name.upper()}...")
        try:
            provider = get_provider(provider_name)
            response = provider.generate(test_prompt, max_tokens=200)
            
            print(f"✅ {provider_name.upper()} response:")
            print(f"   {response[:200]}...")
            print(f"   Stats: {provider.get_stats()}\n")
        except Exception as e:
            print(f"❌ {provider_name.upper()} failed: {e}\n")
    
    print("="*70 + "\n")


if __name__ == "__main__":
    # Test the providers
    test_providers()

