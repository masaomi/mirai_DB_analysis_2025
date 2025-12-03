"""Persona Assembly for multi-perspective analysis."""

import asyncio
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum

from config.settings import Settings, get_settings
from core.llm_client import LLMClient


class PersonaType(str, Enum):
    """Pre-defined persona types."""
    POLICY_MAKER = "policy_maker"
    CITIZEN = "citizen"
    CRITIC = "critic"
    MINORITY_ADVOCATE = "minority_advocate"
    TECHNICAL_EXPERT = "technical_expert"
    ECONOMIST = "economist"


@dataclass
class Persona:
    """A persona for analysis."""
    name: str
    description: str
    system_prompt: str
    focus_areas: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "focus_areas": self.focus_areas,
        }


# Pre-defined personas
PREDEFINED_PERSONAS = {
    PersonaType.POLICY_MAKER: Persona(
        name="政策立案者",
        description="政策立案の観点から分析を行う専門家",
        system_prompt="""あなたは政策立案者の視点でアンケート結果を分析します。
以下の観点を重視してください：
- 政策への実装可能性
- 予算・リソースの制約
- 法的・制度的な課題
- 実現までのロードマップ
- ステークホルダーとの調整""",
        focus_areas=["実装可能性", "制度設計", "予算", "ロードマップ"],
    ),
    PersonaType.CITIZEN: Persona(
        name="一般市民代表",
        description="一般市民の立場から意見を代弁する",
        system_prompt="""あなたは一般市民の代表として分析を行います。
以下の観点を重視してください：
- 日常生活への影響
- わかりやすさ・理解しやすさ
- 公平性・公正性
- 弱者への配慮
- 実感できるメリット""",
        focus_areas=["生活への影響", "公平性", "わかりやすさ", "弱者配慮"],
    ),
    PersonaType.CRITIC: Persona(
        name="批判的研究者",
        description="批判的な視点で潜在的な問題点を指摘する",
        system_prompt="""あなたは批判的な研究者として分析を行います。
以下の観点を重視してください：
- 潜在的なリスクや問題点
- 見落とされている論点
- データの限界や偏り
- 長期的な影響
- 意図しない結果の可能性""",
        focus_areas=["リスク", "見落とし", "データの限界", "長期影響"],
    ),
    PersonaType.MINORITY_ADVOCATE: Persona(
        name="少数派の代弁者",
        description="マイノリティの意見を重視し代弁する",
        system_prompt="""あなたは少数派・マイノリティの代弁者として分析を行います。
以下の観点を重視してください：
- 少数意見の中の重要な視点
- 多数派に埋もれがちな声
- 特定のグループへの影響
- 多様性の確保
- 包摂性の観点""",
        focus_areas=["少数意見", "多様性", "包摂性", "特定グループへの影響"],
    ),
    PersonaType.TECHNICAL_EXPERT: Persona(
        name="技術専門家",
        description="技術的な観点から実現可能性を評価する",
        system_prompt="""あなたは技術専門家として分析を行います。
以下の観点を重視してください：
- 技術的な実現可能性
- 必要なインフラや基盤
- セキュリティ・プライバシーの課題
- スケーラビリティ
- 技術的なリスクと対策""",
        focus_areas=["技術的実現性", "インフラ", "セキュリティ", "スケーラビリティ"],
    ),
    PersonaType.ECONOMIST: Persona(
        name="経済専門家",
        description="経済的な観点から費用対効果を評価する",
        system_prompt="""あなたは経済専門家として分析を行います。
以下の観点を重視してください：
- コストベネフィット分析
- 経済的な波及効果
- 雇用への影響
- 市場への影響
- 持続可能性""",
        focus_areas=["費用対効果", "経済波及効果", "雇用影響", "持続可能性"],
    ),
}


@dataclass
class PersonaAnalysis:
    """Analysis from a single persona."""
    persona: Persona
    analysis: str
    key_points: List[str]
    concerns: List[str]
    recommendations: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "persona": self.persona.to_dict(),
            "analysis": self.analysis[:500] if len(self.analysis) > 500 else self.analysis,
            "key_points": self.key_points,
            "concerns": self.concerns,
            "recommendations": self.recommendations,
        }


@dataclass
class AssembledAnalysis:
    """Combined analysis from all personas."""
    individual_analyses: List[PersonaAnalysis]
    synthesized_summary: str
    common_themes: List[str]
    divergent_views: List[str]
    comprehensive_recommendations: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "individual_analyses": [a.to_dict() for a in self.individual_analyses],
            "synthesized_summary": self.synthesized_summary,
            "common_themes": self.common_themes,
            "divergent_views": self.divergent_views,
            "comprehensive_recommendations": self.comprehensive_recommendations,
        }


PERSONA_ANALYSIS_PROMPT = """## 分析対象
{content}

## 指示
上記の内容を、あなたの専門的視点から分析してください。

以下の形式でJSON出力してください：
{{
    "analysis": "あなたの視点からの分析（200-300字）",
    "key_points": ["重要なポイント1", "重要なポイント2", ...],
    "concerns": ["懸念点1", "懸念点2", ...],
    "recommendations": ["推奨事項1", "推奨事項2", ...]
}}
"""

SYNTHESIS_PROMPT = """以下は異なる専門家視点からの分析結果です。これらを統合して総合的な分析を作成してください。

## 各専門家の分析
{analyses}

## 指示
以下の形式でJSON出力してください：
{{
    "synthesized_summary": "統合された要約（300-500字）",
    "common_themes": ["共通するテーマ1", "共通するテーマ2", ...],
    "divergent_views": ["意見が分かれる点1", "意見が分かれる点2", ...],
    "comprehensive_recommendations": ["総合的な推奨事項1", "総合的な推奨事項2", ...]
}}
"""


class PersonaAssembly:
    """Assemble multiple personas for multi-perspective analysis."""
    
    def __init__(
        self,
        settings: Optional[Settings] = None,
        llm_client: Optional[LLMClient] = None,
        personas: Optional[List[Persona]] = None,
    ):
        """Initialize persona assembly.
        
        Args:
            settings: Application settings
            llm_client: LLM client
            personas: List of personas to use (uses predefined if not specified)
        """
        self.settings = settings or get_settings()
        self.llm_client = llm_client or LLMClient(self.settings)
        
        # Use predefined personas if not specified
        if personas:
            self.personas = personas
        else:
            self.personas = [
                PREDEFINED_PERSONAS[PersonaType.POLICY_MAKER],
                PREDEFINED_PERSONAS[PersonaType.CITIZEN],
                PREDEFINED_PERSONAS[PersonaType.CRITIC],
                PREDEFINED_PERSONAS[PersonaType.MINORITY_ADVOCATE],
            ]
    
    async def analyze_with_persona(
        self,
        persona: Persona,
        content: str,
    ) -> PersonaAnalysis:
        """Analyze content with a specific persona.
        
        Args:
            persona: Persona to use
            content: Content to analyze
            
        Returns:
            PersonaAnalysis object
        """
        prompt = PERSONA_ANALYSIS_PROMPT.format(content=content)
        
        response = await self.llm_client.generate(
            prompt=prompt,
            system_prompt=persona.system_prompt,
        )
        
        # Parse response
        try:
            import json
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                data = json.loads(response[json_start:json_end])
            else:
                raise ValueError("No JSON found")
            
            return PersonaAnalysis(
                persona=persona,
                analysis=data.get("analysis", ""),
                key_points=data.get("key_points", []),
                concerns=data.get("concerns", []),
                recommendations=data.get("recommendations", []),
            )
        except Exception:
            return PersonaAnalysis(
                persona=persona,
                analysis=response[:500],
                key_points=[],
                concerns=[],
                recommendations=[],
            )
    
    async def assemble_analysis(
        self,
        content: str,
    ) -> AssembledAnalysis:
        """Run analysis with all personas and synthesize results.
        
        Args:
            content: Content to analyze
            
        Returns:
            AssembledAnalysis object
        """
        # Run all persona analyses in parallel
        tasks = [
            self.analyze_with_persona(persona, content)
            for persona in self.personas
        ]
        
        individual_analyses = await asyncio.gather(*tasks)
        
        # Synthesize results
        analyses_text = "\n\n".join(
            f"### {a.persona.name}\n"
            f"**分析**: {a.analysis}\n"
            f"**重要ポイント**: {', '.join(a.key_points)}\n"
            f"**懸念点**: {', '.join(a.concerns)}\n"
            f"**推奨事項**: {', '.join(a.recommendations)}"
            for a in individual_analyses
        )
        
        synthesis_prompt = SYNTHESIS_PROMPT.format(analyses=analyses_text)
        synthesis_response = await self.llm_client.generate(synthesis_prompt)
        
        # Parse synthesis response
        try:
            import json
            json_start = synthesis_response.find('{')
            json_end = synthesis_response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                data = json.loads(synthesis_response[json_start:json_end])
            else:
                raise ValueError("No JSON found")
            
            return AssembledAnalysis(
                individual_analyses=list(individual_analyses),
                synthesized_summary=data.get("synthesized_summary", ""),
                common_themes=data.get("common_themes", []),
                divergent_views=data.get("divergent_views", []),
                comprehensive_recommendations=data.get("comprehensive_recommendations", []),
            )
        except Exception:
            # Fallback
            all_key_points = []
            all_concerns = []
            all_recommendations = []
            
            for a in individual_analyses:
                all_key_points.extend(a.key_points)
                all_concerns.extend(a.concerns)
                all_recommendations.extend(a.recommendations)
            
            return AssembledAnalysis(
                individual_analyses=list(individual_analyses),
                synthesized_summary=synthesis_response[:500],
                common_themes=list(set(all_key_points))[:5],
                divergent_views=list(set(all_concerns))[:5],
                comprehensive_recommendations=list(set(all_recommendations))[:5],
            )
    
    def assemble_analysis_sync(
        self,
        content: str,
    ) -> AssembledAnalysis:
        """Synchronous wrapper for assemble_analysis."""
        return asyncio.run(self.assemble_analysis(content))

