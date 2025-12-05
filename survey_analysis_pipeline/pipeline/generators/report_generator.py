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

{% if filter_stats %}
## 📜 フィルタリング統計

クラスタベースの関連性フィルタリング（効率的なLLM判定）の統計です。

- **全回答数**: {{ filter_stats.total_responses }}
- **全クラスタ数**: {{ filter_stats.total_clusters }}
- **分析対象回答数**: {{ filter_stats.final_responses }}

### クラスタ別フィルタ結果

| フィルタ方法 | クラスタ数 | 説明 |
|------------|----------|------|
| 自動含める（大規模） | {{ filter_stats.auto_included_clusters }} | ≥10件のクラスタは自動的に関連ありと判定 |
| LLMチェック（中規模） | {{ filter_stats.llm_checked_clusters }} | 3-9件のクラスタは代表サンプルをLLM判定 |
| 除外（小規模） | {{ filter_stats.excluded_clusters }} | <3件のクラスタは除外（マイノリティで再評価） |
| ノイズ | {{ filter_stats.noise_responses }}件 | クラスタに属さない回答 |

### 効率性

- **LLMコール数**: {{ filter_stats.llm_calls_made }}回
- **節約したLLMコール**: {{ filter_stats.llm_calls_saved }}回（全件チェック比）

---
{% endif %}

{% if supporting_insights %}
## ✅ 法案をサポートする知見

法案の内容を根拠に基づいてサポートする意見です。

{% for insight in supporting_insights %}
### {{ loop.index }}. {{ insight.content }}

**根拠・背景**: {{ insight.reason }}
{% if insight.related_ronten %}
**関連する論点**: {{ insight.related_ronten }}
{% endif %}

{% endfor %}
{% endif %}

---

{% if concerns %}
## ⚠️ 法案への懸念点

法案の内容に関する懸念事項です。

{% for concern in concerns %}
### {{ loop.index }}. {{ concern.content }}

**想定されるリスク**: {{ concern.risk }}
{% if concern.related_ronten %}
**関連する論点**: {{ concern.related_ronten }}
{% endif %}

{% endfor %}
{% endif %}

---

{% if expert_insights %}
## 💡 専門家・当事者からの重要な指摘

深い専門知識や実務経験に基づく意見です。

{% for insight in expert_insights %}
### {{ loop.index }}. {{ insight.content }}

**専門分野・経験**: {{ insight.expertise }}
{% if insight.related_ronten %}
**関連する論点**: {{ insight.related_ronten }}
{% endif %}

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

{% if ronten_summaries %}
## 📋 論点別分析

法制審議会で議論されている主要論点ごとに、インタビュー結果を整理しました。

{% for ronten in ronten_summaries %}
### {{ loop.index }}. {{ ronten.ronten_title }} (関連意見: {{ ronten.opinion_count }}件)

{{ ronten.summary }}

{% if ronten.supporting_points %}
**サポート意見**:
{% for point in ronten.supporting_points -%}
- {{ point }}
{% endfor %}
{% endif %}

{% if ronten.concern_points %}
**懸念点**:
{% for point in ronten.concern_points -%}
- {{ point }}
{% endfor %}
{% endif %}

{% if ronten.expert_points %}
**専門家・当事者の指摘**:
{% for point in ronten.expert_points -%}
- 💡 {{ point }}
{% endfor %}
{% endif %}

{% if ronten.representative_quotes %}
**代表的な意見**:
{% for quote in ronten.representative_quotes[:2] %}
> "{{ quote[:200] }}{% if quote|length > 200 %}...{% endif %}"

{% endfor %}
{% endif %}

{% if ronten.representative_session_ids %}
**参照セッション**:
{% for session_id in ronten.representative_session_ids[:5] %}
- [セッション {{ session_id[:8] }}...](https://depth-interview-ai.vercel.app/report/{{ session_id }})
{% endfor %}
{% endif %}

{% endfor %}

{% if novel_insights %}
### ★ 新規論点（審議会で議論されていない視点）

以下は法制審議会の論点には含まれていない、新しい視点や指摘です：

{% for insight in novel_insights %}
#### ★ {{ insight.summary }}

> {{ insight.content[:300] }}{% if insight.content|length > 300 %}...{% endif %}

**種別**: {{ insight.insight_type }}
{% if insight.session_id %}
📎 [元のインタビュー](https://depth-interview-ai.vercel.app/report/{{ insight.session_id }})
{% endif %}

{% endfor %}
{% endif %}

---
{% endif %}

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

### スコア詳細

| 指標 | 値 | 説明 |
|------|-----|------|
| **合意スコア** | {{ "%.1f"|format(multi_llm_consensus.agreement_score * 100) }}% | `合意点数 / (合意点数 + 対立点数)` |
{% if multi_llm_consensus.discussion_rounds %}
| **相互評価平均スコア** | {{ "%.1f"|format(multi_llm_consensus.discussion_rounds[-1].consensus_score * 100) }}% | 各LLMが他のLLM回答を評価した平均（0-10点を正規化） |
{% endif %}
| **議論ラウンド数** | {{ multi_llm_consensus.discussion_rounds | length }} | 合意形成までの反復回数 |

### 統合された知見

{{ multi_llm_consensus.consensus_content }}

{% if multi_llm_consensus.disagreements %}
### モデル間で意見が分かれた点

{% for disagreement in multi_llm_consensus.disagreements -%}
- {{ disagreement }}
{% endfor %}
{% endif %}

{% if multi_llm_consensus.referenced_sessions or multi_llm_consensus.referenced_clusters %}
### 参照情報

{% if multi_llm_consensus.referenced_sessions %}
**参照セッション**:
{% for session in multi_llm_consensus.referenced_sessions -%}
- [セッション {{ session }}](https://depth-interview-ai.vercel.app/report/{{ session }})
{% endfor %}
{% endif %}

{% if multi_llm_consensus.referenced_clusters %}
**参照クラスタ**:
{% for cluster_id in multi_llm_consensus.referenced_clusters -%}
- クラスタ {{ cluster_id }}
{% endfor %}
{% endif %}

{% endif %}

### 詳細レポート

- [議論ログ (discussion_log.md)](multi_llm/discussion_log.md)
- [評価マトリクス (evaluation_matrix.json)](multi_llm/evaluation_matrix.json)
- [合意レポート (consensus_report.md)](multi_llm/consensus_report.md)

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
    filter_stats: Optional[Dict[str, Any]] = None  # Added filter stats


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
        
        # Sort cluster summaries by response_count (descending)
        sorted_clusters = sorted(
            summary.cluster_summaries,
            key=lambda cs: cs.response_count,
            reverse=True
        )
        
        context = {
            "survey_title": summary.survey_title,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "date_range": f"{summary.date_range[0]} ～ {summary.date_range[1]}",
            "total_responses": summary.total_responses,
            "executive_summary": summary.executive_summary,
            "stance_distribution": summary.stance_distribution,
            "key_findings": summary.key_findings,
            "cluster_summaries": [cs.to_dict() for cs in sorted_clusters],
            "consensus_points": summary.consensus_points,
            "disagreement_points": summary.disagreement_points,
            "minority_opinions": [mo.to_dict() for mo in summary.minority_opinions],
            "recommended_actions": summary.recommended_actions,
            "caveats": summary.caveats,
            # i-1 Grand Prix: Bill-focused insights
            "supporting_insights": summary.supporting_insights,
            "concerns": summary.concerns,
            # Ronten-based analysis
            "ronten_summaries": [rs.to_dict() for rs in summary.ronten_summaries],
            "novel_insights": [ni.to_dict() for ni in summary.novel_insights],
            "expert_insights": summary.expert_insights,
            # Multi-LLM consensus & filter stats
            "multi_llm_consensus": data.multi_llm_consensus,
            "persona_analysis": data.persona_analysis,
            "filter_stats": data.filter_stats,
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
