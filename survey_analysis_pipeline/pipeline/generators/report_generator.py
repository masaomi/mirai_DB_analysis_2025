"""Generate Markdown and HTML reports."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from jinja2 import Template

from config.settings import Settings, get_settings
from pipeline.summarizers.overall_summarizer import OverallSummary


REPORT_TEMPLATE = """# {{ survey_title }} - 分析レポート

**生成日時**: {{ generated_at }}  
**分析対象期間**: {{ date_range }}  
**総回答数**: {{ total_responses }}件

---

## エグゼクティブサマリー

{{ executive_summary }}

---

{% if supporting_insights %}
## ✅ 法案をサポートする知見

法案の内容を根拠に基づいてサポートする意見です。

{% for insight in supporting_insights %}
### {{ loop.index }}. {{ insight.content }}

**根拠・背景**: {{ insight.reason }}

{% endfor %}
{% endif %}

---

{% if concerns %}
## ⚠️ 法案への懸念点

法案の内容に関する懸念事項です。

{% for concern in concerns %}
### {{ loop.index }}. {{ concern.content }}

**想定されるリスク**: {{ concern.risk }}

{% endfor %}
{% endif %}

---

{% if expert_insights %}
## 💡 専門家・当事者からの重要な指摘

深い専門知識や実務経験に基づく意見です。

{% for insight in expert_insights %}
### {{ loop.index }}. {{ insight.content }}

**専門分野・経験**: {{ insight.expertise }}

{% endfor %}
{% endif %}

---

## 回答者の立場分布

| 立場 | 回答数 | 割合 |
|------|--------|------|
{% for stance, data in stance_distribution.items() -%}
| {{ stance }} | {{ data.count }}件 | {{ "%.1f"|format(data.percentage) }}% |
{% endfor %}

---

## 主要な発見事項

{% for finding in key_findings -%}
{{ loop.index }}. {{ finding }}
{% endfor %}

---

## 意見クラスタ別分析

{% for cluster in cluster_summaries %}
### {{ cluster.cluster_label }} ({{ cluster.response_count }}件)

**このグループの主張**: {{ cluster.group_assertion }}

**主要な論点**:
{% for point in cluster.main_points -%}
- {{ point }}
{% endfor %}

**感情傾向**: {{ cluster.overall_sentiment }}

{% if cluster.representative_quote %}
> 代表的な意見: "{{ cluster.representative_quote }}"
{% endif %}

{% if cluster.distinguishing_features %}
**特徴**: {{ cluster.distinguishing_features | join(', ') }}
{% endif %}

{% if cluster.representative_session_ids %}
**参照セッション**:
{% for session_id in cluster.representative_session_ids[:3] %}
- [セッション {{ session_id[:8] }}...](https://depth-interview-ai.vercel.app/report/{{ session_id }})
{% endfor %}
{% endif %}

{% endfor %}

---

## 合意点と対立点

### ✅ 合意が見られる点

{% for point in consensus_points -%}
- {{ point }}
{% endfor %}

### ⚠️ 意見が分かれる点

{% for point in disagreement_points -%}
- {{ point }}
{% endfor %}

---

## 🔍 注目すべきマイノリティ意見

{% if minority_opinions %}
以下は少数派ながら、独自の視点や重要な指摘を含む意見です：

{% for opinion in minority_opinions %}
### {{ loop.index }}. {{ opinion.uniqueness_reason }} (重要度スコア: {{ "%.2f"|format(opinion.outlier_score) }})

> {{ opinion.content[:300] }}{% if opinion.content|length > 300 %}...{% endif %}

{% if opinion.unique_keywords %}
**独自キーワード**: {{ opinion.unique_keywords | join(', ') }}
{% endif %}

{% if opinion.session_id %}
📎 [元のインタビューを見る](https://depth-interview-ai.vercel.app/report/{{ opinion.session_id }})
{% endif %}

{% endfor %}
{% else %}
特筆すべきマイノリティ意見は検出されませんでした。
{% endif %}

---

## 📋 推奨アクション

{% for action in recommended_actions -%}
{{ loop.index }}. {{ action }}
{% endfor %}

---

## ⚠️ 解釈上の注意点

{% for caveat in caveats -%}
- {{ caveat }}
{% endfor %}

---

{% if multi_llm_consensus %}
## 🤖 Multi-LLM 分析結果

複数のLLMモデルによる分析結果を統合しました。

**合意スコア**: {{ "%.1f"|format(multi_llm_consensus.agreement_score * 100) }}%

### 統合された知見

{{ multi_llm_consensus.consensus_content }}

{% if multi_llm_consensus.disagreements %}
### モデル間で意見が分かれた点

{% for disagreement in multi_llm_consensus.disagreements -%}
- {{ disagreement }}
{% endfor %}
{% endif %}

{% endif %}

{% if persona_analysis %}
## 🎭 多視点分析（ペルソナ分析）

### 統合サマリー

{{ persona_analysis.synthesized_summary }}

### 共通テーマ

{% for theme in persona_analysis.common_themes -%}
- {{ theme }}
{% endfor %}

### 視点の相違

{% for view in persona_analysis.divergent_views -%}
- {{ view }}
{% endfor %}

### 各専門家の視点

{% for analysis in persona_analysis.individual_analyses %}
#### {{ analysis.persona.name }}

{{ analysis.analysis }}

**重要ポイント**: {{ analysis.key_points | join(', ') }}

**懸念点**: {{ analysis.concerns | join(', ') }}

{% endfor %}
{% endif %}

---

*このレポートは自動生成されました。生成日時: {{ generated_at }}*
"""


@dataclass
class ReportData:
    """Data for report generation."""
    overall_summary: OverallSummary
    persona_analysis: Optional[Dict[str, Any]] = None
    multi_llm_consensus: Optional[Dict[str, Any]] = None


class ReportGenerator:
    """Generate reports in various formats."""
    
    def __init__(self, settings: Optional[Settings] = None):
        """Initialize report generator.
        
        Args:
            settings: Application settings
        """
        self.settings = settings or get_settings()
        self.template = Template(REPORT_TEMPLATE)
    
    def generate_markdown(
        self,
        data: ReportData,
    ) -> str:
        """Generate Markdown report.
        
        Args:
            data: Report data
            
        Returns:
            Markdown string
        """
        summary = data.overall_summary
        
        context = {
            "survey_title": summary.survey_title,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "date_range": f"{summary.date_range[0]} ～ {summary.date_range[1]}",
            "total_responses": summary.total_responses,
            "executive_summary": summary.executive_summary,
            "stance_distribution": summary.stance_distribution,
            "key_findings": summary.key_findings,
            "cluster_summaries": [cs.to_dict() for cs in summary.cluster_summaries],
            "consensus_points": summary.consensus_points,
            "disagreement_points": summary.disagreement_points,
            "minority_opinions": [mo.to_dict() for mo in summary.minority_opinions],
            "recommended_actions": summary.recommended_actions,
            "caveats": summary.caveats,
            # i-1 Grand Prix: Bill-focused insights
            "supporting_insights": summary.supporting_insights,
            "concerns": summary.concerns,
            "expert_insights": summary.expert_insights,
            # Multi-LLM consensus
            "multi_llm_consensus": data.multi_llm_consensus,
            "persona_analysis": data.persona_analysis,
        }
        
        return self.template.render(**context)
    
    def generate_html(
        self,
        data: ReportData,
    ) -> str:
        """Generate HTML report.
        
        Args:
            data: Report data
            
        Returns:
            HTML string
        """
        import markdown
        
        md_content = self.generate_markdown(data)
        
        # Convert to HTML
        html_body = markdown.markdown(
            md_content,
            extensions=['tables', 'fenced_code', 'toc'],
        )
        
        # Wrap in HTML template
        html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{data.overall_summary.survey_title} - 分析レポート</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Hiragino Sans', sans-serif;
            max-width: 900px;
            margin: 0 auto;
            padding: 2rem;
            line-height: 1.7;
            color: #333;
            background-color: #fafafa;
        }}
        h1 {{
            color: #1a1a1a;
            border-bottom: 3px solid #007bff;
            padding-bottom: 0.5rem;
        }}
        h2 {{
            color: #2c3e50;
            margin-top: 2rem;
            border-left: 4px solid #007bff;
            padding-left: 1rem;
        }}
        h3 {{
            color: #34495e;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 1rem 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 0.75rem;
            text-align: left;
        }}
        th {{
            background-color: #007bff;
            color: white;
        }}
        tr:nth-child(even) {{
            background-color: #f8f9fa;
        }}
        blockquote {{
            border-left: 4px solid #007bff;
            margin: 1rem 0;
            padding: 0.5rem 1rem;
            background-color: #e8f4fd;
            font-style: italic;
        }}
        hr {{
            border: none;
            border-top: 1px solid #ddd;
            margin: 2rem 0;
        }}
        .highlight {{
            background-color: #fff3cd;
            padding: 0.2rem 0.4rem;
            border-radius: 3px;
        }}
        code {{
            background-color: #f4f4f4;
            padding: 0.2rem 0.4rem;
            border-radius: 3px;
            font-family: 'Monaco', 'Menlo', monospace;
        }}
    </style>
</head>
<body>
{html_body}
</body>
</html>
"""
        return html
    
    def save_report(
        self,
        data: ReportData,
        output_dir: Path,
        formats: list = None,
    ) -> Dict[str, Path]:
        """Save report in specified formats.
        
        Args:
            data: Report data
            output_dir: Output directory
            formats: List of formats ('md', 'html')
            
        Returns:
            Dictionary mapping format to output path
        """
        formats = formats or ['md', 'html']
        output_dir.mkdir(parents=True, exist_ok=True)
        
        outputs = {}
        
        if 'md' in formats:
            md_content = self.generate_markdown(data)
            md_path = output_dir / "report.md"
            md_path.write_text(md_content, encoding='utf-8')
            outputs['md'] = md_path
        
        if 'html' in formats:
            html_content = self.generate_html(data)
            html_path = output_dir / "report.html"
            html_path.write_text(html_content, encoding='utf-8')
            outputs['html'] = html_path
        
        return outputs

