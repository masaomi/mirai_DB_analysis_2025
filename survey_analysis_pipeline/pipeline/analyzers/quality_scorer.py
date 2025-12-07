"""Qualitative scoring for opinion clusters using LLM."""

import json
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from config.settings import Settings, get_settings
from core.llm_client import LLMClient
from pipeline.summarizers.cluster_summarizer import ClusterSummary


SCORING_PROMPT = """あなたは政策分析の専門家です。以下の意見グループ（クラスタ）の要約を読み、その意見の「質」を3つの観点から評価してください。

## 評価対象の意見グループ
- 主張: {group_assertion}
- 主要論点: {main_points}
- 代表的意見: {representative_quote}
- 特徴: {distinguishing_features}

## 評価基準（0.0〜1.0のスコア）

1. **専門性 (Expertise)**: 
   - 実務経験、専門用語の適切な使用、具体的実例、現場の知識が含まれているか
   - 0.0 (素人的) 〜 1.0 (高度に専門的・実務的)

2. **具体性 (Specificity)**:
   - 数字、データ、ケーススタディ、具体的な改善案が含まれているか
   - 0.0 (抽象的・感覚的) 〜 1.0 (具体的・定量的)

3. **新規性 (Novelty)**:
   - 一般的な議論（賛成/反対の二項対立やよくある論点）を超えた独自の視点、逆説的な指摘、新しい切り口があるか
   - 0.0 (ありふれた意見) 〜 1.0 (独自の鋭い視点)

## 出力形式
以下のJSON形式のみを出力してください。説明は不要です。

{{
    "expertise_score": 0.5,
    "specificity_score": 0.5,
    "novelty_score": 0.5,
    "expertise_indicators": ["専門用語の使用", "実務経験への言及"],
    "reasoning": "評価の理由を簡潔に"
}}
"""


@dataclass
class QualityScore:
    """Quality score for a cluster."""
    expertise_score: float = 0.0
    specificity_score: float = 0.0
    novelty_score: float = 0.0
    combined_score: float = 0.0
    expertise_indicators: List[str] = field(default_factory=list)
    reasoning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "expertise_score": self.expertise_score,
            "specificity_score": self.specificity_score,
            "novelty_score": self.novelty_score,
            "combined_score": self.combined_score,
            "expertise_indicators": self.expertise_indicators,
            "reasoning": self.reasoning,
        }


class QualityScorer:
    """Score clusters based on qualitative metrics."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        llm_client: Optional[LLMClient] = None,
    ):
        """Initialize quality scorer.

        Args:
            settings: Application settings
            llm_client: LLM client
        """
        self.settings = settings or get_settings()
        self.llm_client = llm_client or LLMClient(self.settings)

    def calculate_combined_score(self, expertise: float, specificity: float, novelty: float) -> float:
        """Calculate weighted combined score."""
        w_exp = self.settings.quality_score_weight_expertise
        w_spec = self.settings.quality_score_weight_specificity
        w_nov = self.settings.quality_score_weight_novelty
        
        # Normalize weights if they don't sum to 1
        total_weight = w_exp + w_spec + w_nov
        if total_weight > 0:
            w_exp /= total_weight
            w_spec /= total_weight
            w_nov /= total_weight
            
        return (expertise * w_exp) + (specificity * w_spec) + (novelty * w_nov)

    async def score_cluster(self, summary: ClusterSummary) -> QualityScore:
        """Score a single cluster summary.

        Args:
            summary: Cluster summary to score

        Returns:
            QualityScore object
        """
        prompt = SCORING_PROMPT.format(
            group_assertion=summary.group_assertion,
            main_points=", ".join(summary.main_points),
            representative_quote=summary.representative_quote,
            distinguishing_features=", ".join(summary.distinguishing_features),
        )

        try:
            response = await self.llm_client.generate(prompt)
            
            # Parse JSON
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                data = json.loads(response[json_start:json_end])
                
                expertise = float(data.get("expertise_score", 0.0))
                specificity = float(data.get("specificity_score", 0.0))
                novelty = float(data.get("novelty_score", 0.0))
                
                combined = self.calculate_combined_score(expertise, specificity, novelty)
                
                return QualityScore(
                    expertise_score=expertise,
                    specificity_score=specificity,
                    novelty_score=novelty,
                    combined_score=combined,
                    expertise_indicators=data.get("expertise_indicators", []),
                    reasoning=data.get("reasoning", "")
                )
            else:
                return QualityScore()
                
        except Exception as e:
            print(f"Error scoring cluster {summary.cluster_id}: {e}")
            return QualityScore()

    async def score_all_clusters(
        self,
        summaries: List[ClusterSummary],
    ) -> List[ClusterSummary]:
        """Score all cluster summaries.

        Args:
            summaries: List of cluster summaries

        Returns:
            List of cluster summaries with scores attached (modified in-place)
        """
        # Process in parallel with semaphore if needed, but for now sequential/gathered
        # Using gather for parallel execution
        import asyncio
        
        tasks = [self.score_cluster(s) for s in summaries]
        scores = await asyncio.gather(*tasks)
        
        for summary, score in zip(summaries, scores):
            summary.quality_score = score
            
        return summaries
