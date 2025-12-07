"""Summarize clusters of responses using LLM."""

import asyncio
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from config.settings import Settings, get_settings
from core.llm_client import LLMClient
from pipeline.analyzers.topic_clusterer import ClusterResult
from .chunk_summarizer import ChunkSummarizer, ChunkSummary


CLUSTER_MERGE_PROMPT = """あなたはアンケート分析の専門家です。以下は同じクラスタ（類似した意見グループ）に属する回答群の個別要約です。
これらを統合して、このクラスタ全体を代表する要約を作成してください。

## クラスタ情報
- クラスタラベル: {cluster_label}
- 総回答数: {total_responses}
- キーワード: {keywords}

## 個別要約
{chunk_summaries}

## 指示
以下の形式で統合要約を作成してください：

1. **このグループの主張**: このクラスタに属する人々が共通して主張していること
2. **主要な論点**: 重要な論点を5つ以内で
3. **代表的な意見**: 最も代表的な意見の引用（原文に近い形で）
4. **感情傾向**: 全体的な感情傾向
5. **このグループの特徴**: 他のグループと区別される特徴

JSON形式で出力してください：
{{
    "group_assertion": "このグループの主張",
    "main_points": ["論点1", "論点2", ...],
    "representative_quote": "代表的な意見の引用",
    "overall_sentiment": "肯定的/否定的/中立的/混在",
    "distinguishing_features": ["特徴1", "特徴2", ...]
}}
"""


@dataclass
class ClusterSummary:
    """Summary of a response cluster."""
    cluster_id: int
    cluster_label: str
    response_count: int
    group_assertion: str
    main_points: List[str]
    representative_quote: str
    overall_sentiment: str
    distinguishing_features: List[str]
    keywords: List[str]
    chunk_summaries: List[ChunkSummary]
    representative_session_ids: List[str] = None  # Session IDs for reference URLs
    quality_score: Optional[Any] = None  # QualityScore object (avoid circular import)
    
    def __post_init__(self):
        if self.representative_session_ids is None:
            self.representative_session_ids = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "cluster_id": self.cluster_id,
            "cluster_label": self.cluster_label,
            "response_count": self.response_count,
            "group_assertion": self.group_assertion,
            "main_points": self.main_points,
            "representative_quote": self.representative_quote,
            "overall_sentiment": self.overall_sentiment,
            "distinguishing_features": self.distinguishing_features,
            "keywords": self.keywords,
            "representative_session_ids": self.representative_session_ids,
            "quality_score": self.quality_score.to_dict() if self.quality_score else None,
        }


class ClusterSummarizer:
    """Summarize response clusters using hierarchical summarization."""
    
    def __init__(
        self,
        settings: Optional[Settings] = None,
        llm_client: Optional[LLMClient] = None,
    ):
        """Initialize cluster summarizer.
        
        Args:
            settings: Application settings
            llm_client: LLM client
        """
        self.settings = settings or get_settings()
        self.llm_client = llm_client or LLMClient(self.settings)
        self.chunk_summarizer = ChunkSummarizer(self.settings, self.llm_client)
    
    async def summarize_cluster(
        self,
        cluster: ClusterResult,
    ) -> ClusterSummary:
        """Summarize a single cluster using hierarchical approach.
        
        1. Split cluster responses into chunks
        2. Summarize each chunk (Map phase)
        3. Merge chunk summaries (Reduce phase)
        
        Args:
            cluster: Cluster result with responses
            
        Returns:
            ClusterSummary object
        """
        # Extract representative session IDs from cluster responses
        representative_session_ids = []
        if cluster.responses:
            # Get unique session IDs (up to 5 representatives)
            seen_ids = set()
            for resp in cluster.responses[:10]:
                if hasattr(resp, 'session_id') and resp.session_id not in seen_ids:
                    representative_session_ids.append(resp.session_id)
                    seen_ids.add(resp.session_id)
                if len(representative_session_ids) >= 5:
                    break
        
        # Step 1-2: Summarize chunks
        chunk_summaries = await self.chunk_summarizer.summarize_all_chunks(
            cluster.responses
        )
        
        # Step 3: Merge chunk summaries
        if len(chunk_summaries) == 1:
            # Only one chunk, use it directly
            cs = chunk_summaries[0]
            return ClusterSummary(
                cluster_id=cluster.cluster_id,
                cluster_label=cluster.label,
                response_count=cluster.size,
                group_assertion=cs.main_opinion,
                main_points=cs.key_points,
                representative_quote=cs.raw_responses[0][:300] if cs.raw_responses else "",
                overall_sentiment=cs.sentiment,
                distinguishing_features=cs.unique_perspectives,
                keywords=cluster.keywords,
                chunk_summaries=chunk_summaries,
                representative_session_ids=representative_session_ids,
            )
        
        # Format chunk summaries for merge prompt
        summaries_text = "\n\n".join(
            f"### チャンク {cs.chunk_id + 1} ({cs.response_count}件)\n"
            f"- 主要意見: {cs.main_opinion}\n"
            f"- キーポイント: {', '.join(cs.key_points)}\n"
            f"- 感情傾向: {cs.sentiment}\n"
            f"- ユニークな視点: {', '.join(cs.unique_perspectives)}"
            for cs in chunk_summaries
        )
        
        prompt = CLUSTER_MERGE_PROMPT.format(
            cluster_label=cluster.label,
            total_responses=cluster.size,
            keywords=", ".join(cluster.keywords),
            chunk_summaries=summaries_text,
        )
        
        # Call LLM for merge
        response = await self.llm_client.generate(prompt)
        
        # Parse response
        try:
            import json
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                data = json.loads(response[json_start:json_end])
            else:
                raise ValueError("No JSON found")
            
            return ClusterSummary(
                cluster_id=cluster.cluster_id,
                cluster_label=cluster.label,
                response_count=cluster.size,
                group_assertion=data.get("group_assertion", ""),
                main_points=data.get("main_points", []),
                representative_quote=data.get("representative_quote", ""),
                overall_sentiment=data.get("overall_sentiment", "不明"),
                distinguishing_features=data.get("distinguishing_features", []),
                keywords=cluster.keywords,
                chunk_summaries=chunk_summaries,
                representative_session_ids=representative_session_ids,
            )
        except Exception:
            # Fallback
            all_opinions = [cs.main_opinion for cs in chunk_summaries]
            all_points = []
            for cs in chunk_summaries:
                all_points.extend(cs.key_points)
            
            return ClusterSummary(
                cluster_id=cluster.cluster_id,
                cluster_label=cluster.label,
                response_count=cluster.size,
                group_assertion=" / ".join(all_opinions[:3]),
                main_points=list(set(all_points))[:5],
                representative_quote=chunk_summaries[0].raw_responses[0][:300] if chunk_summaries and chunk_summaries[0].raw_responses else "",
                overall_sentiment="混在",
                distinguishing_features=[],
                keywords=cluster.keywords,
                chunk_summaries=chunk_summaries,
                representative_session_ids=representative_session_ids,
            )
    
    async def summarize_all_clusters(
        self,
        clusters: List[ClusterResult],
    ) -> List[ClusterSummary]:
        """Summarize all clusters.
        
        Args:
            clusters: List of cluster results
            
        Returns:
            List of ClusterSummary objects
        """
        summaries = []
        for cluster in clusters:
            summary = await self.summarize_cluster(cluster)
            summaries.append(summary)
        return summaries
    
    def summarize_all_clusters_sync(
        self,
        clusters: List[ClusterResult],
    ) -> List[ClusterSummary]:
        """Synchronous wrapper for summarize_all_clusters."""
        return asyncio.run(self.summarize_all_clusters(clusters))

