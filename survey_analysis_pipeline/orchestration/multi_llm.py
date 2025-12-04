"""Multi-LLM Orchestration for consensus-based analysis."""

import asyncio
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from collections import Counter

import litellm

from config.settings import Settings, get_settings


@dataclass
class LLMResponse:
    """Response from a single LLM."""
    model: str
    content: str
    tokens_used: int = 0
    latency_ms: float = 0.0


@dataclass 
class ConsensusResult:
    """Result of multi-LLM consensus."""
    consensus_content: str
    agreement_score: float
    individual_responses: List[LLMResponse]
    disagreements: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "consensus_content": self.consensus_content,
            "agreement_score": self.agreement_score,
            "individual_responses": [
                {"model": r.model, "content": r.content[:500]}
                for r in self.individual_responses
            ],
            "disagreements": self.disagreements,
        }


CONSENSUS_PROMPT = """以下は複数のAIモデルによる同じ質問への回答です。
これらの回答を統合し、合意点を抽出してください。

## 各モデルの回答
{responses}

## 指示
1. 全てのモデルが同意している点を抽出してください
2. 意見が分かれている点があれば記載してください
3. 統合した最終回答を作成してください

JSON形式で出力してください：
{{
    "consensus": "統合された回答",
    "agreement_points": ["合意点1", "合意点2", ...],
    "disagreement_points": ["意見が分かれた点1", ...]
}}
"""


class MultiLLMOrchestrator:
    """Orchestrate multiple LLMs for consensus-based analysis."""
    
    def __init__(
        self,
        settings: Optional[Settings] = None,
        models: Optional[List[str]] = None,
    ):
        """Initialize multi-LLM orchestrator.
        
        Args:
            settings: Application settings
            models: List of model identifiers to use
        """
        self.settings = settings or get_settings()
        self.models = models or self.settings.multi_llm_models
        
        # Ensure we have at least one model
        if not self.models:
            raise ValueError("At least one model must be specified")
    
    async def _call_model(
        self,
        model: str,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> LLMResponse:
        """Call a single model.
        
        Args:
            model: Model identifier
            prompt: User prompt
            system_prompt: Optional system prompt
            
        Returns:
            LLMResponse object
        """
        import time
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        start_time = time.time()
        
        # Add openrouter/ prefix if not present and using OpenRouter
        model_name = model
        if not model.startswith("openrouter/") and self.settings.openrouter_api_key:
            model_name = f"openrouter/{model}"
        
        try:
            # Build kwargs for litellm
            kwargs = {
                "model": model_name,
                "messages": messages,
                "temperature": self.settings.temperature,
                "max_tokens": self.settings.max_tokens,
            }
            
            # Add OpenRouter API key and base URL if available
            if self.settings.openrouter_api_key:
                kwargs["api_key"] = self.settings.openrouter_api_key
                kwargs["api_base"] = self.settings.openrouter_base_url
            
            response = await litellm.acompletion(**kwargs)
            
            content = response.choices[0].message.content
            tokens = response.usage.total_tokens if response.usage else 0
            latency = (time.time() - start_time) * 1000
            
            return LLMResponse(
                model=model,
                content=content,
                tokens_used=tokens,
                latency_ms=latency,
            )
        except Exception as e:
            return LLMResponse(
                model=model,
                content=f"Error: {str(e)}",
                tokens_used=0,
                latency_ms=(time.time() - start_time) * 1000,
            )
    
    async def gather_responses(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> List[LLMResponse]:
        """Gather responses from all models in parallel.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            
        Returns:
            List of LLMResponse objects
        """
        tasks = [
            self._call_model(model, prompt, system_prompt)
            for model in self.models
        ]
        
        responses = await asyncio.gather(*tasks)
        return list(responses)
    
    async def reach_consensus(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        consensus_model: Optional[str] = None,
    ) -> ConsensusResult:
        """Gather responses and reach consensus.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            consensus_model: Model to use for consensus (uses first model if not specified)
            
        Returns:
            ConsensusResult object
        """
        # Gather individual responses
        responses = await self.gather_responses(prompt, system_prompt)
        
        # Filter out errors
        valid_responses = [r for r in responses if not r.content.startswith("Error:")]
        
        if not valid_responses:
            return ConsensusResult(
                consensus_content="All models failed to respond",
                agreement_score=0.0,
                individual_responses=responses,
                disagreements=["No valid responses received"],
            )
        
        if len(valid_responses) == 1:
            return ConsensusResult(
                consensus_content=valid_responses[0].content,
                agreement_score=1.0,
                individual_responses=responses,
                disagreements=[],
            )
        
        # Format responses for consensus prompt
        responses_text = "\n\n".join(
            f"### {r.model}\n{r.content}"
            for r in valid_responses
        )
        
        consensus_prompt = CONSENSUS_PROMPT.format(responses=responses_text)
        
        # Use specified model or first model for consensus
        consensus_model = consensus_model or self.models[0]
        
        consensus_response = await self._call_model(
            consensus_model,
            consensus_prompt,
        )
        
        # Parse consensus response
        try:
            import json
            json_start = consensus_response.content.find('{')
            json_end = consensus_response.content.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                data = json.loads(consensus_response.content[json_start:json_end])
            else:
                raise ValueError("No JSON found")
            
            # Calculate agreement score based on number of agreement points
            num_agreements = len(data.get("agreement_points", []))
            num_disagreements = len(data.get("disagreement_points", []))
            total = num_agreements + num_disagreements
            agreement_score = num_agreements / total if total > 0 else 0.5
            
            return ConsensusResult(
                consensus_content=data.get("consensus", ""),
                agreement_score=agreement_score,
                individual_responses=responses,
                disagreements=data.get("disagreement_points", []),
            )
        except Exception:
            # Fallback: use first response as consensus
            return ConsensusResult(
                consensus_content=valid_responses[0].content,
                agreement_score=0.5,
                individual_responses=responses,
                disagreements=["Failed to parse consensus response"],
            )
    
    def gather_responses_sync(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> List[LLMResponse]:
        """Synchronous wrapper for gather_responses."""
        return asyncio.run(self.gather_responses(prompt, system_prompt))
    
    def reach_consensus_sync(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        consensus_model: Optional[str] = None,
    ) -> ConsensusResult:
        """Synchronous wrapper for reach_consensus."""
        return asyncio.run(self.reach_consensus(prompt, system_prompt, consensus_model))

