"""Match opinions/clusters to legislative discussion points (ronten)."""

import asyncio
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from pipeline.extractors.ronten_loader import RontenItem, RontenLoader
from config.settings import Settings, get_settings
from core.llm_client import LLMClient


@dataclass
class RontenMatch:
    """Result of matching an opinion to ronten items."""
    matched_ronten_ids: List[str]  # IDs of matched ronten items
    matched_ronten_titles: List[str]  # Titles of matched ronten items
    is_novel: bool  # True if no ronten match found (novel perspective)
    confidence: float  # Confidence score 0-1
    insight_type: str  # "supporting", "concern", "expert", "general"
    summary: str  # Brief summary of the opinion's relevance
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "matched_ronten_ids": self.matched_ronten_ids,
            "matched_ronten_titles": self.matched_ronten_titles,
            "is_novel": self.is_novel,
            "confidence": self.confidence,
            "insight_type": self.insight_type,
            "summary": self.summary,
        }


@dataclass
class RontenAnalysis:
    """Analysis results organized by ronten."""
    ronten_id: str
    ronten_title: str
    opinion_count: int
    supporting_opinions: List[Dict[str, Any]] = field(default_factory=list)
    concerns: List[Dict[str, Any]] = field(default_factory=list)
    expert_opinions: List[Dict[str, Any]] = field(default_factory=list)
    general_opinions: List[Dict[str, Any]] = field(default_factory=list)
    summary: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "ronten_id": self.ronten_id,
            "ronten_title": self.ronten_title,
            "opinion_count": self.opinion_count,
            "supporting_opinions": self.supporting_opinions,
            "concerns": self.concerns,
            "expert_opinions": self.expert_opinions,
            "general_opinions": self.general_opinions,
            "summary": self.summary,
        }


RONTEN_MATCH_PROMPT = """あなたは法案検討を支援する分析専門家です。以下の意見が、法制審議会で議論されている論点のどれに関連するかを判定してください。

## 法制審議会の主要論点
{ronten_list}

## 分析対象の意見
{content}

## 指示
1. この意見が上記のどの論点に関連するか判定してください（複数可）
2. どの論点にも該当しない場合は「novel」とマークしてください
3. 意見の種類を判定してください：
   - supporting: 法案をサポートする意見（メリット、賛成理由など）
   - concern: 法案への懸念（リスク、反対理由、課題など）
   - expert: 専門知識・実務経験に基づく具体的指摘
   - general: 一般的な意見・感想

## 出力形式（JSON）
{{
    "matched_ronten_ids": ["functional_equivalence", "control_concept"],  // 関連する論点ID（なければ空配列）
    "is_novel": false,  // 論点に該当しない新しい視点かどうか
    "confidence": 0.8,  // 判定の確信度 (0-1)
    "insight_type": "concern",  // supporting/concern/expert/general
    "summary": "この意見の論点との関連を1-2文で説明"
}}
"""


class RontenMatcher:
    """Match opinions to legislative discussion points."""
    
    def __init__(
        self,
        settings: Optional[Settings] = None,
        llm_client: Optional[LLMClient] = None,
    ):
        """Initialize matcher."""
        self.settings = settings or get_settings()
        self.llm_client = llm_client or LLMClient(self.settings)
        self.ronten_loader = RontenLoader(self.settings)
    
    def _format_ronten_list(self, items: List[RontenItem]) -> str:
        """Format ronten items for prompt."""
        lines = []
        for item in items:
            lines.append(f"- **{item.id}** ({item.title}): {item.description}")
        return "\n".join(lines)
    
    async def match_opinion(
        self,
        content: str,
        survey_slug: str,
    ) -> RontenMatch:
        """Match a single opinion to ronten items.
        
        Args:
            content: Opinion content
            survey_slug: Survey slug for loading relevant ronten
            
        Returns:
            RontenMatch result
        """
        ronten_items = self.ronten_loader.get_ronten_items(survey_slug)
        
        if not ronten_items:
            # No ronten defined, mark as novel
            return RontenMatch(
                matched_ronten_ids=[],
                matched_ronten_titles=[],
                is_novel=True,
                confidence=1.0,
                insight_type="general",
                summary="論点情報なし",
            )
        
        ronten_list = self._format_ronten_list(ronten_items)
        ronten_id_to_title = {item.id: item.title for item in ronten_items}
        
        prompt = RONTEN_MATCH_PROMPT.format(
            ronten_list=ronten_list,
            content=content[:1000],  # Truncate long content
        )
        
        try:
            response = await self.llm_client.generate(prompt)
            
            # Parse JSON
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                data = json.loads(response[json_start:json_end])
                
                matched_ids = data.get("matched_ronten_ids", [])
                matched_titles = [ronten_id_to_title.get(rid, rid) for rid in matched_ids]
                
                return RontenMatch(
                    matched_ronten_ids=matched_ids,
                    matched_ronten_titles=matched_titles,
                    is_novel=data.get("is_novel", len(matched_ids) == 0),
                    confidence=float(data.get("confidence", 0.5)),
                    insight_type=data.get("insight_type", "general"),
                    summary=data.get("summary", ""),
                )
            else:
                raise ValueError("No JSON found in response")
                
        except Exception as e:
            # Fallback: use keyword matching
            return self._keyword_match(content, ronten_items)
    
    def _keyword_match(
        self,
        content: str,
        ronten_items: List[RontenItem],
    ) -> RontenMatch:
        """Simple keyword-based matching as fallback."""
        content_lower = content.lower()
        matched_ids = []
        matched_titles = []
        
        for item in ronten_items:
            for keyword in item.keywords:
                if keyword.lower() in content_lower:
                    if item.id not in matched_ids:
                        matched_ids.append(item.id)
                        matched_titles.append(item.title)
                    break
        
        return RontenMatch(
            matched_ronten_ids=matched_ids,
            matched_ronten_titles=matched_titles,
            is_novel=len(matched_ids) == 0,
            confidence=0.3,  # Lower confidence for keyword match
            insight_type="general",
            summary="キーワードマッチング（LLMフォールバック）",
        )
    
    async def match_opinions_batch(
        self,
        contents: List[str],
        survey_slug: str,
    ) -> List[RontenMatch]:
        """Match multiple opinions in parallel.
        
        Args:
            contents: List of opinion contents
            survey_slug: Survey slug
            
        Returns:
            List of RontenMatch results
        """
        tasks = [self.match_opinion(content, survey_slug) for content in contents]
        return await asyncio.gather(*tasks)
    
    async def analyze_by_ronten(
        self,
        opinions: List[Dict[str, Any]],
        survey_slug: str,
    ) -> tuple[List[RontenAnalysis], List[Dict[str, Any]]]:
        """Analyze opinions and group by ronten.
        
        Args:
            opinions: List of opinion dicts with 'content' key
            survey_slug: Survey slug
            
        Returns:
            Tuple of (ronten_analyses, novel_opinions)
        """
        ronten_items = self.ronten_loader.get_ronten_items(survey_slug)
        
        if not ronten_items or not opinions:
            return [], []
        
        # Match all opinions
        contents = [op.get("content", "") for op in opinions]
        matches = await self.match_opinions_batch(contents, survey_slug)
        
        # Group by ronten
        ronten_dict: Dict[str, RontenAnalysis] = {}
        for item in ronten_items:
            ronten_dict[item.id] = RontenAnalysis(
                ronten_id=item.id,
                ronten_title=item.title,
                opinion_count=0,
            )
        
        novel_opinions: List[Dict[str, Any]] = []
        
        for i, (opinion, match) in enumerate(zip(opinions, matches)):
            opinion_with_match = {
                **opinion,
                "ronten_match": match.to_dict(),
            }
            
            if match.is_novel:
                novel_opinions.append(opinion_with_match)
            else:
                for ronten_id in match.matched_ronten_ids:
                    if ronten_id in ronten_dict:
                        analysis = ronten_dict[ronten_id]
                        analysis.opinion_count += 1
                        
                        if match.insight_type == "supporting":
                            analysis.supporting_opinions.append(opinion_with_match)
                        elif match.insight_type == "concern":
                            analysis.concerns.append(opinion_with_match)
                        elif match.insight_type == "expert":
                            analysis.expert_opinions.append(opinion_with_match)
                        else:
                            analysis.general_opinions.append(opinion_with_match)
        
        # Filter out empty ronten and sort by opinion count
        analyses = [a for a in ronten_dict.values() if a.opinion_count > 0]
        analyses.sort(key=lambda x: x.opinion_count, reverse=True)
        
        return analyses, novel_opinions
    
    def match_opinion_sync(self, content: str, survey_slug: str) -> RontenMatch:
        """Synchronous wrapper for match_opinion."""
        return asyncio.run(self.match_opinion(content, survey_slug))
    
    def analyze_by_ronten_sync(
        self,
        opinions: List[Dict[str, Any]],
        survey_slug: str,
    ) -> tuple[List[RontenAnalysis], List[Dict[str, Any]]]:
        """Synchronous wrapper for analyze_by_ronten."""
        return asyncio.run(self.analyze_by_ronten(opinions, survey_slug))

