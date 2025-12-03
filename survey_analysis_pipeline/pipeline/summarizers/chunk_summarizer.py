"""Summarize chunks of responses using LLM (Map phase)."""

import asyncio
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from config.settings import Settings, get_settings
from core.llm_client import LLMClient
from pipeline.extractors.response_extractor import UserResponse


CHUNK_SUMMARY_PROMPT = """あなたはアンケート分析の専門家です。以下のアンケート回答群を分析し、要約してください。

## 回答一覧
{responses}

## 指示
以下の観点で要約してください：

1. **主要な意見**: この回答群で最も多く見られる意見（1-2文）
2. **キーポイント**: 重要なポイントを3-5個の箇条書きで
3. **感情傾向**: 肯定的/否定的/中立的のどれが優勢か
4. **特徴的な視点**: 興味深い・ユニークな意見があれば

JSON形式で出力してください：
{{
    "main_opinion": "主要な意見の要約",
    "key_points": ["ポイント1", "ポイント2", ...],
    "sentiment": "肯定的/否定的/中立的",
    "unique_perspectives": ["ユニークな視点1", ...]
}}
"""


@dataclass
class ChunkSummary:
    """Summary of a response chunk."""
    chunk_id: int
    response_count: int
    main_opinion: str
    key_points: List[str]
    sentiment: str
    unique_perspectives: List[str]
    raw_responses: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "chunk_id": self.chunk_id,
            "response_count": self.response_count,
            "main_opinion": self.main_opinion,
            "key_points": self.key_points,
            "sentiment": self.sentiment,
            "unique_perspectives": self.unique_perspectives,
        }


class ChunkSummarizer:
    """Summarize response chunks using LLM (Map phase of Map-Reduce)."""
    
    def __init__(
        self,
        settings: Optional[Settings] = None,
        llm_client: Optional[LLMClient] = None,
    ):
        """Initialize chunk summarizer.
        
        Args:
            settings: Application settings
            llm_client: LLM client (creates new one if not provided)
        """
        self.settings = settings or get_settings()
        self.llm_client = llm_client or LLMClient(self.settings)
        self.chunk_size = self.settings.chunk_size
    
    def split_into_chunks(
        self,
        responses: List[UserResponse]
    ) -> List[List[UserResponse]]:
        """Split responses into chunks for processing.
        
        Args:
            responses: List of all responses
            
        Returns:
            List of response chunks
        """
        chunks = []
        for i in range(0, len(responses), self.chunk_size):
            chunk = responses[i:i + self.chunk_size]
            chunks.append(chunk)
        return chunks
    
    async def summarize_chunk(
        self,
        chunk: List[UserResponse],
        chunk_id: int,
    ) -> ChunkSummary:
        """Summarize a single chunk of responses.
        
        Args:
            chunk: List of responses in this chunk
            chunk_id: Identifier for this chunk
            
        Returns:
            ChunkSummary object
        """
        # Format responses for prompt
        responses_text = "\n---\n".join(
            f"回答{i+1}: {r.content[:500]}" for i, r in enumerate(chunk)
        )
        
        prompt = CHUNK_SUMMARY_PROMPT.format(responses=responses_text)
        
        # Call LLM
        response = await self.llm_client.generate(prompt)
        
        # Parse response
        try:
            import json
            # Try to extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                data = json.loads(json_str)
            else:
                raise ValueError("No JSON found in response")
            
            return ChunkSummary(
                chunk_id=chunk_id,
                response_count=len(chunk),
                main_opinion=data.get("main_opinion", ""),
                key_points=data.get("key_points", []),
                sentiment=data.get("sentiment", "中立的"),
                unique_perspectives=data.get("unique_perspectives", []),
                raw_responses=[r.content for r in chunk],
            )
        except Exception as e:
            # Fallback: use raw response as summary
            return ChunkSummary(
                chunk_id=chunk_id,
                response_count=len(chunk),
                main_opinion=response[:500],
                key_points=[],
                sentiment="不明",
                unique_perspectives=[],
                raw_responses=[r.content for r in chunk],
            )
    
    async def summarize_all_chunks(
        self,
        responses: List[UserResponse],
        parallel: bool = True,
    ) -> List[ChunkSummary]:
        """Summarize all response chunks.
        
        Args:
            responses: All responses to summarize
            parallel: Whether to process chunks in parallel
            
        Returns:
            List of ChunkSummary objects
        """
        chunks = self.split_into_chunks(responses)
        
        if parallel:
            # Process in parallel
            tasks = [
                self.summarize_chunk(chunk, i)
                for i, chunk in enumerate(chunks)
            ]
            summaries = await asyncio.gather(*tasks)
        else:
            # Process sequentially
            summaries = []
            for i, chunk in enumerate(chunks):
                summary = await self.summarize_chunk(chunk, i)
                summaries.append(summary)
        
        return list(summaries)
    
    def summarize_all_chunks_sync(
        self,
        responses: List[UserResponse],
        parallel: bool = True,
    ) -> List[ChunkSummary]:
        """Synchronous wrapper for summarize_all_chunks."""
        return asyncio.run(self.summarize_all_chunks(responses, parallel))

