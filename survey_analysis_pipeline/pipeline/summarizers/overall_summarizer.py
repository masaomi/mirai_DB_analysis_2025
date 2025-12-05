"""Generate overall summary from cluster summaries."""

import asyncio
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, TYPE_CHECKING

from config.settings import Settings, get_settings
from core.llm_client import LLMClient
from pipeline.analyzers.stance_detector import StanceResult
from pipeline.analyzers.minority_detector import MinorityOpinion
from .cluster_summarizer import ClusterSummary

if TYPE_CHECKING:
    from orchestration.multi_llm import MultiLLMOrchestrator, ConsensusResult


OVERALL_SUMMARY_PROMPT = """あなたは法案検討を支援するアンケート分析の専門家です。
以下のインタビュー分析結果と法制審議会の論点（コンテキスト）を踏まえて、法案を検討する際に参考になる知見を抽出し、レポートを作成してください。

## 法制審議会での主な論点（コンテキスト）
{ronten_context}

## インタビュー情報
- テーマ: {survey_title}
- 総回答数: {total_responses}
- 実施期間: {date_range}

## 立場分布
{stance_distribution}

## クラスタ別要約
{cluster_summaries}

## 注目すべきマイノリティ意見
{minority_opinions}

## 指示
法案検討に役立つ知見を抽出し、以下の形式で分析を作成してください。
特に、法制審議会の論点（電子裏書、強制執行、システム障害時の対応など）に関連する、専門知識・実務経験・当事者経験に基づく具体的な意見を重視してください。

1. **エグゼクティブサマリー**: 意思決定者向けの簡潔な要約（200字以内）
2. **法案をサポートする知見**: 法案の内容を根拠に基づいてサポートする意見
   - 例: 「実務においてこういう課題がある」「この法案が可決するとこういう観点で嬉しい」
   - コンテキストのどの論点に関連するかを明記してください。
3. **法案への懸念点**: 法案の内容に関する懸念
   - 例: 「これが実現するとこういう不都合・リスクがある」「運用コストが高い割にインパクトが小さい」
   - コンテキストのどの論点に関連するかを明記してください。
4. **専門家・当事者からの重要な指摘**: 深い専門知識や実務経験に基づく意見
5. **合意点**: 回答者間で共通している意見
6. **対立点**: 意見が分かれている論点
7. **推奨アクション**: 分析結果に基づく推奨事項
8. **注意点**: 解釈時に注意すべき点

JSON形式で出力してください：
{{
    "executive_summary": "エグゼクティブサマリー",
    "supporting_insights": [
        {{"content": "サポートする知見1", "reason": "根拠や背景", "related_ronten": "関連論点（例：電子裏書）"}},
        {{"content": "サポートする知見2", "reason": "根拠や背景", "related_ronten": "関連論点（例：B案）"}}
    ],
    "concerns": [
        {{"content": "懸念点1", "risk": "想定されるリスク", "related_ronten": "関連論点（例：強制執行）"}},
        {{"content": "懸念点2", "risk": "想定されるリスク", "related_ronten": "関連論点"}}
    ],
    "expert_insights": [
        {{"content": "専門家の指摘1", "expertise": "専門分野や経験", "related_ronten": "関連論点"}},
        {{"content": "専門家の指摘2", "expertise": "専門分野や経験", "related_ronten": "関連論点"}}
    ],
    "key_findings": ["発見1", "発見2", ...],
    "consensus_points": ["合意点1", "合意点2", ...],
    "disagreement_points": ["対立点1", "対立点2", ...],
    "recommended_actions": ["推奨1", "推奨2", ...],
    "caveats": ["注意点1", "注意点2", ...]
}}
"""


@dataclass
class RontenSummary:
    """Summary for a single ronten (discussion point)."""
    ronten_id: str
    ronten_title: str
    opinion_count: int
    summary: str  # LLM-generated summary for this ronten
    supporting_points: List[str] = field(default_factory=list)
    concern_points: List[str] = field(default_factory=list)
    expert_points: List[str] = field(default_factory=list)
    representative_quotes: List[str] = field(default_factory=list)
    representative_session_ids: List[str] = field(default_factory=list)  # Session IDs for reference
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "ronten_id": self.ronten_id,
            "ronten_title": self.ronten_title,
            "opinion_count": self.opinion_count,
            "summary": self.summary,
            "supporting_points": self.supporting_points,
            "concern_points": self.concern_points,
            "expert_points": self.expert_points,
            "representative_quotes": self.representative_quotes,
            "representative_session_ids": self.representative_session_ids,
        }


@dataclass
class NovelInsight:
    """A novel insight not covered by existing ronten."""
    content: str
    session_id: str
    insight_type: str  # "supporting", "concern", "expert", "general"
    summary: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "session_id": self.session_id,
            "insight_type": self.insight_type,
            "summary": self.summary,
        }


@dataclass
class OverallSummary:
    """Overall summary of survey analysis."""
    survey_title: str
    total_responses: int
    date_range: tuple[str, str]
    
    # Summary content
    executive_summary: str
    key_findings: List[str]
    consensus_points: List[str]
    disagreement_points: List[str]
    recommended_actions: List[str]
    caveats: List[str]
    
    # i-1 Grand Prix: Bill-focused insights
    supporting_insights: List[Dict[str, str]] = field(default_factory=list)  # {"content": ..., "reason": ..., "related_ronten": ...}
    concerns: List[Dict[str, str]] = field(default_factory=list)  # {"content": ..., "risk": ..., "related_ronten": ...}
    expert_insights: List[Dict[str, str]] = field(default_factory=list)  # {"content": ..., "expertise": ..., "related_ronten": ...}
    
    # Ronten-based analysis
    ronten_summaries: List[RontenSummary] = field(default_factory=list)
    novel_insights: List[NovelInsight] = field(default_factory=list)
    
    # Components
    stance_distribution: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    cluster_summaries: List[ClusterSummary] = field(default_factory=list)
    minority_opinions: List[MinorityOpinion] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "survey_title": self.survey_title,
            "total_responses": self.total_responses,
            "date_range": self.date_range,
            "executive_summary": self.executive_summary,
            "key_findings": self.key_findings,
            "consensus_points": self.consensus_points,
            "disagreement_points": self.disagreement_points,
            "recommended_actions": self.recommended_actions,
            "caveats": self.caveats,
            "supporting_insights": self.supporting_insights,
            "concerns": self.concerns,
            "expert_insights": self.expert_insights,
            "ronten_summaries": [rs.to_dict() for rs in self.ronten_summaries],
            "novel_insights": [ni.to_dict() for ni in self.novel_insights],
            "stance_distribution": self.stance_distribution,
            "cluster_summaries": [cs.to_dict() for cs in self.cluster_summaries],
            "minority_opinions": [mo.to_dict() for mo in self.minority_opinions],
        }


class OverallSummarizer:
    """Generate overall summary from all analysis components."""
    
    def __init__(
        self,
        settings: Optional[Settings] = None,
        llm_client: Optional[LLMClient] = None,
    ):
        """Initialize overall summarizer.
        
        Args:
            settings: Application settings
            llm_client: LLM client
        """
        self.settings = settings or get_settings()
        self.llm_client = llm_client or LLMClient(self.settings)
    
    async def generate_summary(
        self,
        survey_title: str,
        total_responses: int,
        date_range: tuple[str, str],
        stance_distribution: Dict[str, Dict[str, Any]],
        cluster_summaries: List[ClusterSummary],
        minority_opinions: List[MinorityOpinion],
        ronten_context: str = "",
    ) -> OverallSummary:
        """Generate overall summary from analysis components.
        
        Args:
            survey_title: Survey title
            total_responses: Total number of responses
            date_range: Date range tuple
            stance_distribution: Stance distribution data
            cluster_summaries: List of cluster summaries
            minority_opinions: List of minority opinions
            ronten_context: Context string regarding legal issues (ronten)
            
        Returns:
            OverallSummary object
        """
        # Format stance distribution
        stance_text = "\n".join(
            f"- {stance}: {data['count']}件 ({data['percentage']:.1f}%)"
            for stance, data in stance_distribution.items()
        )
        
        # Format cluster summaries
        clusters_text = "\n\n".join(
            f"### {cs.cluster_label} ({cs.response_count}件)\n"
            f"**主張**: {cs.group_assertion}\n"
            f"**論点**: {', '.join(cs.main_points)}\n"
            f"**感情傾向**: {cs.overall_sentiment}\n"
            f"**特徴**: {', '.join(cs.distinguishing_features)}"
            for cs in cluster_summaries
        )
        
        # Format minority opinions
        minorities_text = "\n".join(
            f"- (スコア: {mo.outlier_score:.2f}) {mo.content[:200]}..."
            for mo in minority_opinions[:5]
        ) if minority_opinions else "特になし"
        
        # Build prompt
        # Truncate ronten context if too long
        context_str = ronten_context[:3000] if ronten_context else "（特になし）"
        
        prompt = OVERALL_SUMMARY_PROMPT.format(
            survey_title=survey_title,
            total_responses=total_responses,
            date_range=f"{date_range[0]} ～ {date_range[1]}",
            stance_distribution=stance_text,
            cluster_summaries=clusters_text,
            minority_opinions=minorities_text,
            ronten_context=context_str,
        )
        
        # Call LLM
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
            
            return OverallSummary(
                survey_title=survey_title,
                total_responses=total_responses,
                date_range=date_range,
                executive_summary=data.get("executive_summary", ""),
                key_findings=data.get("key_findings", []),
                consensus_points=data.get("consensus_points", []),
                disagreement_points=data.get("disagreement_points", []),
                recommended_actions=data.get("recommended_actions", []),
                caveats=data.get("caveats", []),
                supporting_insights=data.get("supporting_insights", []),
                concerns=data.get("concerns", []),
                expert_insights=data.get("expert_insights", []),
                stance_distribution=stance_distribution,
                cluster_summaries=cluster_summaries,
                minority_opinions=minority_opinions,
            )
        except Exception:
            # Fallback
            return OverallSummary(
                survey_title=survey_title,
                total_responses=total_responses,
                date_range=date_range,
                executive_summary=response[:500],
                key_findings=[],
                consensus_points=[],
                disagreement_points=[],
                recommended_actions=[],
                caveats=["要約の解析に失敗しました。LLMの生出力を確認してください。"],
                supporting_insights=[],
                concerns=[],
                expert_insights=[],
                stance_distribution=stance_distribution,
                cluster_summaries=cluster_summaries,
                minority_opinions=minority_opinions,
            )
    
    def generate_summary_sync(
        self,
        survey_title: str,
        total_responses: int,
        date_range: tuple[str, str],
        stance_distribution: Dict[str, Dict[str, Any]],
        cluster_summaries: List[ClusterSummary],
        minority_opinions: List[MinorityOpinion],
    ) -> OverallSummary:
        """Synchronous wrapper for generate_summary."""
        return asyncio.run(self.generate_summary(
            survey_title=survey_title,
            total_responses=total_responses,
            date_range=date_range,
            stance_distribution=stance_distribution,
            cluster_summaries=cluster_summaries,
            minority_opinions=minority_opinions,
        ))
    
    async def generate_summary_multi_llm(
        self,
        orchestrator: "MultiLLMOrchestrator",
        survey_title: str,
        total_responses: int,
        date_range: tuple[str, str],
        stance_distribution: Dict[str, Dict[str, Any]],
        cluster_summaries: List[ClusterSummary],
        minority_opinions: List[MinorityOpinion],
        ronten_context: str = "",
    ) -> tuple["OverallSummary", "ConsensusResult"]:
        """Generate overall summary using Multi-LLM consensus.
        
        Args:
            orchestrator: MultiLLMOrchestrator instance
            survey_title: Survey title
            total_responses: Total number of responses
            date_range: Date range tuple
            stance_distribution: Stance distribution data
            cluster_summaries: List of cluster summaries
            minority_opinions: List of minority opinions
            ronten_context: Context string regarding legal issues (ronten)
            
        Returns:
            Tuple of (OverallSummary, ConsensusResult)
        """
        # Format stance distribution
        stance_text = "\n".join(
            f"- {stance}: {data['count']}件 ({data['percentage']:.1f}%)"
            for stance, data in stance_distribution.items()
        )
        
        # Format cluster summaries with cluster IDs and session IDs
        clusters_text = "\n\n".join(
            f"### クラスタ {cs.cluster_id}: {cs.cluster_label} ({cs.response_count}件)\n"
            f"**主張**: {cs.group_assertion}\n"
            f"**論点**: {', '.join(cs.main_points)}\n"
            f"**感情傾向**: {cs.overall_sentiment}\n"
            f"**特徴**: {', '.join(cs.distinguishing_features)}\n"
            f"**代表的セッション**: {', '.join(getattr(cs, 'representative_session_ids', [])[:3])}"
            for cs in cluster_summaries
        )
        
        # Format minority opinions with session IDs
        minorities_text = "\n".join(
            f"- (セッション: {mo.session_id}, スコア: {mo.outlier_score:.2f}) {mo.content[:200]}..."
            for mo in minority_opinions[:10]
        ) if minority_opinions else "特になし"
        
        # Build prompt
        # Truncate ronten context if too long
        context_str = ronten_context[:3000] if ronten_context else "（特になし）"
        
        prompt = OVERALL_SUMMARY_PROMPT.format(
            survey_title=survey_title,
            total_responses=total_responses,
            date_range=f"{date_range[0]} ～ {date_range[1]}",
            stance_distribution=stance_text,
            cluster_summaries=clusters_text,
            minority_opinions=minorities_text,
            ronten_context=context_str,
        )
        
        # Add instruction to include references and consider context
        prompt += """
        
        重要: 
        1. 分析結果には、可能な限り根拠となるセッションIDやクラスタIDを含めてください。
        2. 法制審議会の論点コンテキストとの関連性を必ず明記してください（特にsupporting/concerns/expertセクション）。
        """
        
        # Use Multi-LLM consensus
        consensus_result = await orchestrator.reach_consensus_iterative(
            prompt,
            system_prompt="あなたは法案分析の専門家です。多角的な視点から法案の影響を分析し、建設的な提言を行ってください。法制審議会の議論状況を踏まえた深い分析を求めます。"
        )
        
        # Parse consensus content
        try:
            content = consensus_result.consensus_content
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                data = json.loads(content[json_start:json_end])
            else:
                raise ValueError("No JSON found in consensus")
            
            summary = OverallSummary(
                survey_title=survey_title,
                total_responses=total_responses,
                date_range=date_range,
                executive_summary=data.get("executive_summary", ""),
                key_findings=data.get("key_findings", []),
                consensus_points=data.get("consensus_points", []),
                disagreement_points=data.get("disagreement_points", []),
                recommended_actions=data.get("recommended_actions", []),
                caveats=data.get("caveats", []),
                supporting_insights=data.get("supporting_insights", []),
                concerns=data.get("concerns", []),
                expert_insights=data.get("expert_insights", []),
                stance_distribution=stance_distribution,
                cluster_summaries=cluster_summaries,
                minority_opinions=minority_opinions,
            )
        except Exception:
            # Fallback: use consensus content as executive summary
            summary = OverallSummary(
                survey_title=survey_title,
                total_responses=total_responses,
                date_range=date_range,
                executive_summary=consensus_result.consensus_content[:500] if consensus_result.consensus_content else "",
                key_findings=[],
                consensus_points=consensus_result.agreement_points if hasattr(consensus_result, 'agreement_points') else [],
                disagreement_points=consensus_result.disagreements,
                recommended_actions=[],
                caveats=["Multi-LLM合意形成の結果を解析できませんでした。"],
                supporting_insights=[],
                concerns=[],
                expert_insights=[],
                stance_distribution=stance_distribution,
                cluster_summaries=cluster_summaries,
                minority_opinions=minority_opinions,
            )
        
        return summary, consensus_result

