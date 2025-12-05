"""Cluster-based relevance filter - filters after clustering to reduce API calls."""

import asyncio
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple

from pipeline.extractors.response_extractor import UserResponse
from pipeline.analyzers.topic_clusterer import ClusterResult
from config.settings import Settings, get_settings
from core.llm_client import LLMClient


@dataclass
class ClusterFilterResult:
    """Result of cluster-level filtering."""
    cluster_id: int
    cluster_label: str
    cluster_size: int
    is_relevant: bool
    filter_method: str  # "auto_include", "llm_check", "excluded"
    relevance_score: float
    reason: str
    checked_samples: int = 0  # How many samples were LLM-checked
    related_ronten: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "cluster_id": int(self.cluster_id),  # Convert numpy int64 to Python int
            "cluster_label": self.cluster_label,
            "cluster_size": int(self.cluster_size),
            "is_relevant": self.is_relevant,
            "filter_method": self.filter_method,
            "relevance_score": float(self.relevance_score),
            "reason": self.reason,
            "checked_samples": int(self.checked_samples),
            "related_ronten": self.related_ronten,
        }


@dataclass 
class ClusterFilterStats:
    """Statistics for cluster-based filtering."""
    total_responses: int
    total_clusters: int
    auto_included_clusters: int
    llm_checked_clusters: int
    excluded_clusters: int
    noise_responses: int
    noise_relevant: int
    final_responses: int
    llm_calls_made: int
    llm_calls_saved: int  # Compared to per-response filtering
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_responses": self.total_responses,
            "total_clusters": self.total_clusters,
            "auto_included_clusters": self.auto_included_clusters,
            "llm_checked_clusters": self.llm_checked_clusters,
            "excluded_clusters": self.excluded_clusters,
            "noise_responses": self.noise_responses,
            "noise_relevant": self.noise_relevant,
            "final_responses": self.final_responses,
            "llm_calls_made": self.llm_calls_made,
            "llm_calls_saved": self.llm_calls_saved,
        }


CLUSTER_RELEVANCE_PROMPT = """以下のクラスタ（回答グループ）が「{survey_title}」に関する法案検討に参考になる知見を含むか判定してください。

## 法制審議会での主な論点（コンテキスト）
{ronten_context}

## クラスタ情報
- ラベル: {cluster_label}
- サイズ: {cluster_size}件
- キーワード: {keywords}

## 代表的な回答サンプル
{sample_responses}

## 判定基準

### 関連あり（relevant: true）
- 法案の論点に関係する具体的な意見
- 実務上の課題・メリット・デメリット
- 専門知識・当事者経験に基づく懸念や指摘

### 関連なし（relevant: false）- 必ず除外
以下のカテゴリは法案検討に無関係なので**必ず除外**してください：

1. **挨拶・謝辞**: 「ありがとう」「お疲れ様」「頑張ってください」等
2. **システム・UIへの意見**: 「このアンケートの質問が〜」「AIの回答が〜」「学習データが〜」等
3. **空虚・無意味な回答**: 「わからない」「特になし」「あああ」等
4. **テーマ無関係**: 法案と全く関係ない話題
5. **政党・選挙への一般的応援**: 法案の内容に触れない単なる応援メッセージ

JSON形式で出力してください：
{{
    "relevant": true/false,
    "score": 0.0〜1.0,
    "reason": "判定理由",
    "exclusion_category": "除外の場合のカテゴリ（挨拶・謝辞/システム意見/空虚/無関係/応援のみ）",
    "related_ronten": "関連する論点（あれば）"
}}
"""


class ClusterBasedFilter:
    """Filter responses based on cluster characteristics to reduce API calls."""
    
    def __init__(
        self,
        settings: Optional[Settings] = None,
        llm_client: Optional[LLMClient] = None,
    ):
        self.settings = settings or get_settings()
        self.llm_client = llm_client or LLMClient(self.settings)
        
        # Thresholds
        self.auto_include_threshold = self.settings.min_cluster_size_for_report  # 10
        self.medium_cluster_min = 3
        self.samples_to_check = 2  # For medium clusters
    
    async def filter_clusters(
        self,
        clusters: List[ClusterResult],
        survey_title: str,
        ronten_context: str = "",
    ) -> Tuple[List[ClusterResult], List[ClusterFilterResult], ClusterFilterStats]:
        """Filter clusters based on size and representative sample checks.
        
        Strategy:
        - Large clusters (≥10): Auto-include (clearly on-topic by clustering)
        - Medium clusters (3-9): LLM check 1-2 representative samples
        - Small clusters (<3) and noise (-1): Handled separately as potential minorities
        
        Args:
            clusters: List of ClusterResult objects
            survey_title: Survey title
            ronten_context: Legal issues context
            
        Returns:
            Tuple of (filtered_clusters, filter_results, stats)
        """
        filter_results: List[ClusterFilterResult] = []
        included_clusters: List[ClusterResult] = []
        
        # Stats tracking
        auto_included = 0
        llm_checked = 0
        excluded = 0
        llm_calls = 0
        noise_count = 0
        noise_relevant = 0
        
        total_responses = sum(c.size for c in clusters)
        
        for cluster in clusters:
            # Noise cluster (cluster_id == -1) - handle separately
            if cluster.cluster_id == -1:
                noise_count = cluster.size
                # We'll filter noise responses individually for minorities later
                # For now, mark as excluded from main clusters but track count
                filter_results.append(ClusterFilterResult(
                    cluster_id=-1,
                    cluster_label="Noise",
                    cluster_size=cluster.size,
                    is_relevant=False,
                    filter_method="noise_separate",
                    relevance_score=0.0,
                    reason="ノイズクラスタは個別にマイノリティ検出で処理",
                    checked_samples=0,
                ))
                continue
            
            # Large clusters: Auto-include
            if cluster.size >= self.auto_include_threshold:
                auto_included += 1
                included_clusters.append(cluster)
                filter_results.append(ClusterFilterResult(
                    cluster_id=cluster.cluster_id,
                    cluster_label=cluster.label,
                    cluster_size=cluster.size,
                    is_relevant=True,
                    filter_method="auto_include",
                    relevance_score=1.0,
                    reason=f"大規模クラスタ（{cluster.size}件 ≥ {self.auto_include_threshold}）は自動的に関連ありと判定",
                    checked_samples=0,
                ))
                
            # Medium clusters: LLM check
            elif cluster.size >= self.medium_cluster_min:
                llm_checked += 1
                result = await self._check_cluster_relevance(
                    cluster, survey_title, ronten_context
                )
                llm_calls += 1
                filter_results.append(result)
                
                if result.is_relevant:
                    included_clusters.append(cluster)
                else:
                    excluded += 1
                    
            # Small clusters: Exclude from main analysis (may be picked up as minorities)
            else:
                excluded += 1
                filter_results.append(ClusterFilterResult(
                    cluster_id=cluster.cluster_id,
                    cluster_label=cluster.label,
                    cluster_size=cluster.size,
                    is_relevant=False,
                    filter_method="excluded_small",
                    relevance_score=0.0,
                    reason=f"小規模クラスタ（{cluster.size}件 < {self.medium_cluster_min}）は除外（マイノリティ検出で再評価）",
                    checked_samples=0,
                ))
        
        # Calculate stats
        final_responses = sum(c.size for c in included_clusters)
        llm_calls_saved = total_responses - llm_calls  # Compared to per-response filtering
        
        stats = ClusterFilterStats(
            total_responses=total_responses,
            total_clusters=len([c for c in clusters if c.cluster_id != -1]),
            auto_included_clusters=auto_included,
            llm_checked_clusters=llm_checked,
            excluded_clusters=excluded,
            noise_responses=noise_count,
            noise_relevant=noise_relevant,
            final_responses=final_responses,
            llm_calls_made=llm_calls,
            llm_calls_saved=llm_calls_saved,
        )
        
        return included_clusters, filter_results, stats
    
    async def _check_cluster_relevance(
        self,
        cluster: ClusterResult,
        survey_title: str,
        ronten_context: str,
    ) -> ClusterFilterResult:
        """Check relevance of a medium-sized cluster using LLM."""
        # Get sample responses
        samples = cluster.responses[:self.samples_to_check]
        sample_text = "\n\n".join(
            f"【サンプル{i+1}】{r.content[:300]}..." if len(r.content) > 300 else f"【サンプル{i+1}】{r.content}"
            for i, r in enumerate(samples)
        )
        
        context_str = ronten_context[:2000] if ronten_context else "（特になし）"
        
        prompt = CLUSTER_RELEVANCE_PROMPT.format(
            survey_title=survey_title,
            ronten_context=context_str,
            cluster_label=cluster.label,
            cluster_size=cluster.size,
            keywords=", ".join(cluster.keywords[:10]),
            sample_responses=sample_text,
        )
        
        try:
            response = await self.llm_client.generate(prompt)
            
            # Parse JSON
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                data = json.loads(response[json_start:json_end])
                
                return ClusterFilterResult(
                    cluster_id=cluster.cluster_id,
                    cluster_label=cluster.label,
                    cluster_size=cluster.size,
                    is_relevant=data.get("relevant", True),
                    filter_method="llm_check",
                    relevance_score=float(data.get("score", 0.5)),
                    reason=data.get("reason", "LLM判定"),
                    checked_samples=len(samples),
                    related_ronten=data.get("related_ronten", ""),
                )
            else:
                # Fallback: include if parsing fails
                return ClusterFilterResult(
                    cluster_id=cluster.cluster_id,
                    cluster_label=cluster.label,
                    cluster_size=cluster.size,
                    is_relevant=True,
                    filter_method="llm_check_fallback",
                    relevance_score=0.5,
                    reason="JSON解析失敗、デフォルトで含める",
                    checked_samples=len(samples),
                )
                
        except Exception as e:
            # Fallback: include on error
            return ClusterFilterResult(
                cluster_id=cluster.cluster_id,
                cluster_label=cluster.label,
                cluster_size=cluster.size,
                is_relevant=True,
                filter_method="llm_check_error",
                relevance_score=0.5,
                reason=f"エラー: {str(e)}、デフォルトで含める",
                checked_samples=len(samples),
            )

