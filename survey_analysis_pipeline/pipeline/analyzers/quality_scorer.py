"""Qualitative scoring for opinion clusters using LLM."""

import json
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from config.settings import Settings, get_settings
from core.llm_client import LLMClient
from pipeline.summarizers.cluster_summarizer import ClusterSummary


SCORING_PROMPT = """あなたは政策分析の専門家です。以下の意見グループ（クラスタ）の要約を読み、その意見の「質」を4つの観点から評価してください。

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

4. **政策的価値 (Policy Relevance)**:
   - 政策立案者が法案修正・運用検討時に参考にできるか
   - 具体的な改善提案、リスク指摘、運用上の懸念を含むか
   - 0.0 (政策検討に役立たない) 〜 1.0 (政策立案に直接貢献)

## 出力形式
以下のJSON形式のみを出力してください。各スコアの理由は簡潔に（30文字程度）。

{{
    "expertise_score": 0.5,
    "expertise_reasoning": "専門用語や実務経験に基づく評価の理由",
    "specificity_score": 0.5,
    "specificity_reasoning": "具体性の評価の理由",
    "novelty_score": 0.5,
    "novelty_reasoning": "新規性の評価の理由",
    "policy_relevance_score": 0.5,
    "policy_relevance_reasoning": "政策的価値の評価の理由"
}}
"""


@dataclass
class QualityScore:
    """Quality score for a cluster."""
    expertise_score: float = 0.0
    specificity_score: float = 0.0
    novelty_score: float = 0.0
    policy_relevance_score: float = 0.0  # Added policy relevance
    combined_score: float = 0.0
    # Individual reasoning for each score
    expertise_reasoning: str = ""
    specificity_reasoning: str = ""
    novelty_reasoning: str = ""
    policy_relevance_reasoning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "expertise_score": self.expertise_score,
            "specificity_score": self.specificity_score,
            "novelty_score": self.novelty_score,
            "policy_relevance_score": self.policy_relevance_score,
            "combined_score": self.combined_score,
            "expertise_reasoning": self.expertise_reasoning,
            "specificity_reasoning": self.specificity_reasoning,
            "novelty_reasoning": self.novelty_reasoning,
            "policy_relevance_reasoning": self.policy_relevance_reasoning,
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

    def calculate_combined_score(
        self, 
        expertise: float, 
        specificity: float, 
        novelty: float,
        policy_relevance: float
    ) -> float:
        """Calculate weighted combined score."""
        w_exp = self.settings.quality_score_weight_expertise
        w_spec = self.settings.quality_score_weight_specificity
        w_nov = self.settings.quality_score_weight_novelty
        w_pol = getattr(self.settings, "quality_score_weight_policy", 0.3)  # Default fallback if not in settings
        
        # Normalize weights if they don't sum to 1
        total_weight = w_exp + w_spec + w_nov + w_pol
        if total_weight > 0:
            w_exp /= total_weight
            w_spec /= total_weight
            w_nov /= total_weight
            w_pol /= total_weight
            
        return (expertise * w_exp) + (specificity * w_spec) + (novelty * w_nov) + (policy_relevance * w_pol)

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
                policy_relevance = float(data.get("policy_relevance_score", 0.0))
                
                combined = self.calculate_combined_score(expertise, specificity, novelty, policy_relevance)
                
                return QualityScore(
                    expertise_score=expertise,
                    specificity_score=specificity,
                    novelty_score=novelty,
                    policy_relevance_score=policy_relevance,
                    combined_score=combined,
                    expertise_reasoning=data.get("expertise_reasoning", ""),
                    specificity_reasoning=data.get("specificity_reasoning", ""),
                    novelty_reasoning=data.get("novelty_reasoning", ""),
                    policy_relevance_reasoning=data.get("policy_relevance_reasoning", ""),
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



