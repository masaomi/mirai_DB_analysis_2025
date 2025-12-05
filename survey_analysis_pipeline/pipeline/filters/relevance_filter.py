"""Filter responses by relevance and extract insights."""

import asyncio
import json
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple

from pipeline.extractors.response_extractor import UserResponse
from config.settings import Settings, get_settings
from core.llm_client import LLMClient


@dataclass
class RelevanceResult:
    """Result of relevance check and insight extraction."""
    session_id: str
    is_relevant: bool
    relevance_score: float  # 0.0 to 1.0
    reason: str
    insight_type: str  # "supporting", "concern", "expert", "none"
    extracted_insight: str = ""  # Extracted key insight
    related_ronten: str = ""     # Related issue point from context (if any)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "is_relevant": self.is_relevant,
            "relevance_score": self.relevance_score,
            "reason": self.reason,
            "insight_type": self.insight_type,
            "extracted_insight": self.extracted_insight,
            "related_ronten": self.related_ronten,
        }


RELEVANCE_PROMPT = """以下の回答が「{survey_title}」に関する法案検討に参考になる知見を含むか判定し、重要な知見を抽出してください。

## 法制審議会での主な論点（コンテキスト）
{ronten_context}

## 回答
{content}

## 参考になる知見の基準
1. **法案をサポートする意見**（supporting）
   - 実務課題、メリット等の根拠に基づいているもの
   - 法制審議会の論点（A案/B案/C案、電子裏書、強制執行等）に関連する具体的な支持理由
2. **法案への懸念**（concern）
   - リスク、不都合、運用コスト問題等
   - 論点に対して「ここが不十分だ」「この場合はどうなるのか」といった指摘
3. **専門知識・実務経験に基づく具体的意見**（expert）
   - 現場の具体的な事例や深い洞察を含むもの

## 除外すべき回答（relevant: false）
- 挨拶・お礼・激励のみ
- テーマに関係ない話題
- 内容が短すぎる/空虚な回答（「わからない」「特になし」等）

## 指示
JSON形式で出力してください：
{{
    "relevant": true または false,
    "score": 0.0〜1.0の重要度スコア,
    "reason": "判定理由",
    "type": "supporting" / "concern" / "expert" / "none",
    "insight": "抽出した重要な知見（要約せず、原文の重要な部分を抜き出す）",
    "related_ronten": "関連する主な論点（上記コンテキストから該当するものがあれば記載、なければ空欄）"
}}
"""


class RelevanceFilter:
    """Filter responses by relevance and extract insights."""
    
    def __init__(self, settings: Optional[Settings] = None, llm_client: Optional[LLMClient] = None):
        """Initialize relevance filter.
        
        Args:
            settings: Application settings
            llm_client: LLM client
        """
        self.settings = settings or get_settings()
        self.llm_client = llm_client or LLMClient(self.settings)
    
    async def filter_responses(
        self,
        responses: List[UserResponse],
        survey_title: str,
        ronten_context: str = "",
        batch_size: Optional[int] = None,
    ) -> Tuple[List[UserResponse], List[RelevanceResult]]:
        """Filter responses by relevance and extract insights.
        
        Args:
            responses: List of user responses
            survey_title: Survey title for context
            ronten_context: Context string regarding legal issues (ronten)
            batch_size: Batch size for processing (overrides settings)
            
        Returns:
            Tuple of (filtered responses, relevance results)
        """
        batch_size = batch_size or self.settings.relevance_batch_size
        results: List[RelevanceResult] = []
        
        # Process in batches
        for i in range(0, len(responses), batch_size):
            batch = responses[i : i + batch_size]
            batch_tasks = [
                self._check_relevance(response, survey_title, ronten_context)
                for response in batch
            ]
            batch_results = await asyncio.gather(*batch_tasks)
            results.extend(batch_results)
        
        # Filter responses based on score threshold
        filtered_responses = []
        for response, result in zip(responses, results):
            if result.is_relevant and result.relevance_score >= self.settings.relevance_min_score:
                # Store extraction metadata in the response object (if UserResponse allows dynamic attrs or metadata dict)
                # UserResponse is a Pydantic model, usually rigid. 
                # But we can assume extraction isn't needed for clustering per se, just for the report later.
                # However, the task description implies using insights for summarization.
                # For now, we just filter. The summarizer can re-examine the content or we can pass these results along.
                filtered_responses.append(response)
        
        return filtered_responses, results
    
    async def _check_relevance(
        self,
        response: UserResponse,
        survey_title: str,
        ronten_context: str = "",
    ) -> RelevanceResult:
        """Check relevance of a single response.
        
        Args:
            response: User response
            survey_title: Survey title
            ronten_context: Legal issues context
            
        Returns:
            RelevanceResult object
        """
        # Truncate context if too long to avoid token limits, though ronten files are usually manageable
        # Prioritize ronten context over full response length if needed
        context_str = ronten_context[:2000] if ronten_context else "（特になし）"
        
        prompt = RELEVANCE_PROMPT.format(
            survey_title=survey_title,
            ronten_context=context_str,
            content=response.content[:1000],  # Truncate if too long
        )
        
        try:
            llm_response = await self.llm_client.generate(prompt)
            
            # Parse JSON
            json_start = llm_response.find('{')
            json_end = llm_response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                data = json.loads(llm_response[json_start:json_end])
                
                return RelevanceResult(
                    session_id=response.session_id,
                    is_relevant=data.get("relevant", False),
                    relevance_score=float(data.get("score", 0.0)),
                    reason=data.get("reason", "Parsed successfully"),
                    insight_type=data.get("type", "none"),
                    extracted_insight=data.get("insight", ""),
                    related_ronten=data.get("related_ronten", ""),
                )
            else:
                # Fallback for parsing failure
                return RelevanceResult(
                    session_id=response.session_id,
                    is_relevant=True,  # Default to keep if unsure
                    relevance_score=0.5,
                    reason="JSON parsing failed",
                    insight_type="unknown",
                    extracted_insight="",
                    related_ronten="",
                )
                
        except Exception as e:
            # Fallback for error
            return RelevanceResult(
                session_id=response.session_id,
                is_relevant=True,  # Default to keep
                relevance_score=0.5,
                reason=f"Error: {str(e)}",
                insight_type="error",
                extracted_insight="",
                related_ronten="",
            )

