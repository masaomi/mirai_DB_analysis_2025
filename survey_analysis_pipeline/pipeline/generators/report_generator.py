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

<a id="toc"></a>

## 📑 目次

- [エグゼクティブサマリー](#executive-summary)
- [量的解釈の制約](#quantitative-bias)
{% if filter_stats %}- [フィルタリング統計](#filter-stats){% endif %}
- [回答者の立場分布](#stance-distribution)
- [主要な発見事項](#key-findings)
{% if multi_llm_consensus %}- [Multi-LLM 分析結果](#multi-llm-analysis){% endif %}
{% if ronten_summaries %}- [論点別分析](#ronten-analysis){% endif %}
{% if novel_insights %}- [論点にない新しい視点](#novel-insights){% endif %}
- [質的スコア凡例](#quality-legend)
- [意見クラスタ別分析](#cluster-analysis)
- [合意点と対立点](#consensus-disagreement)
- [マイノリティ意見](#minority-opinions)
- [推奨アクション](#recommended-actions)
- [解釈上の注意点](#caveats)


---

<a id="executive-summary"></a>

## エグゼクティブサマリー

{{ executive_summary }}

---

<a id="quantitative-bias"></a>

## ⚠️ 量的解釈の制約（政治領域固有の注意点）

> **重要**: 本調査は回答者の自己選択に基づく非確率標本調査です。以下の制約を踏まえてお読みください。

| 制約 | 説明 |
|------|------|
| **一人一回答の保証なし** | 同一人物による複数回答を技術的に排除できていません |
| **インセンティブの非対称性** | 法案に強い利害を持つ層（推進派/反対派）が回答しやすい構造です |
| **代表性の欠如** | 回答割合は日本社会全体の意見分布を反映しません |

**本レポートの読み方**: 「何％がこう考えている」ではなく「どのような視点・論点が存在するか」という **意見の多様性のマッピング** としてお読みください。回答数の多寡は意見の重要性や正当性を示すものではありません。

---

{% if filter_stats %}
<a id="filter-stats"></a>

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

<a id="stance-distribution"></a>

## 回答者の立場分布

> ⚠️ この割合は**回答者プール内**の分布であり、社会全体の意見分布を反映するものではありません。

| 立場 | 回答数 | 割合 |
|------|--------|------|
{% for stance, data in stance_distribution.items() -%}
| {{ stance }} | {{ data.count }}件 | {{ "%.1f"|format(data.percentage) }}% |
{% endfor %}

---

<a id="key-findings"></a>

## 主要な発見事項

{% for finding in key_findings -%}
{{ loop.index }}. {{ finding }}
{% endfor %}

---

{% if multi_llm_consensus %}
<a id="multi-llm-analysis"></a>

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
### ⚠️ モデル間で意見が分かれた点

{% for disagreement in multi_llm_consensus.disagreements -%}
- {{ disagreement }}
{% endfor %}
{% endif %}

{% if multi_llm_consensus.referenced_sessions or multi_llm_consensus.referenced_clusters %}
### 参照情報

{% if multi_llm_consensus.referenced_sessions %}
**参照セッション**:
{% for session in multi_llm_consensus.referenced_sessions -%}
- [セッション {{ session[:8] }}...](https://depth-interview-ai.vercel.app/report/{{ session }})
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

---
{% endif %}

{% if ronten_summaries %}
<a id="ronten-analysis"></a>

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
<a id="novel-insights"></a>

## 💡 論点にない新しい視点

法制審議会の議論で明示的に取り上げられていない、回答者から得られた新しい視点です。

{% for insight in novel_insights %}
### {{ loop.index }}. 「{{ insight.summary }}」

{{ insight.content[:300] }}{% if insight.content|length > 300 %}...{% endif %}

{% if insight.session_id %}
📎 [元のインタビューを見る](https://depth-interview-ai.vercel.app/report/{{ insight.session_id }})
{% endif %}

{% endfor %}
{% endif %}

---
{% endif %}

<a id="quality-legend"></a>

## 📊 質的スコア凡例

本レポートでは、各意見クラスタに対して以下の観点から質的評価を行っています：

| 指標 | 説明 | 重み |
|------|------|------|
| **専門性** | 実務経験・業界用語・具体的事例の有無 | 40% |
| **具体性** | 数字・データ・ケーススタディの含有 | 30% |
| **新規性** | 他クラスタにない独自の視点 | 30% |

> 質的スコアが高い意見は、回答数が少なくても政策検討において重要な示唆を含む可能性があります。

---

<a id="cluster-analysis"></a>

## 意見クラスタ別分析

{% for cluster in cluster_summaries %}
### 「{{ cluster.cluster_label }}」 ({{ cluster.response_count }}件)

{% if cluster.quality_score %}
**質的スコア**: {% for i in range(5) %}{% if cluster.quality_score.combined_score >= (i+1)*0.2 %}★{% else %}☆{% endif %}{% endfor %} ({{ "%.2f"|format(cluster.quality_score.combined_score) }})
- 専門性: {{ "%.2f"|format(cluster.quality_score.expertise_score) }}{% if cluster.quality_score.expertise_reasoning %} - {{ cluster.quality_score.expertise_reasoning }}{% endif %}

- 具体性: {{ "%.2f"|format(cluster.quality_score.specificity_score) }}{% if cluster.quality_score.specificity_reasoning %} - {{ cluster.quality_score.specificity_reasoning }}{% endif %}

- 新規性: {{ "%.2f"|format(cluster.quality_score.novelty_score) }}{% if cluster.quality_score.novelty_reasoning %} - {{ cluster.quality_score.novelty_reasoning }}{% endif %}

{% endif %}

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

<a id="consensus-disagreement"></a>

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

<a id="minority-opinions"></a>

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

<a id="recommended-actions"></a>

## 📋 推奨アクション

{% for action in recommended_actions -%}
{{ loop.index }}. {{ action }}
{% endfor %}

---

<a id="caveats"></a>

## ⚠️ 解釈上の注意点

{% for caveat in caveats -%}
- {{ caveat }}
{% endfor %}

---

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
        
        # Sort cluster summaries
        # If quality scoring is enabled and sort is requested, sort by quality score
        # Otherwise sort by response_count
        
        # Determine sorting method
        if (self.settings.quality_scoring_enabled and 
            self.settings.quality_score_sort_clusters and 
            any(cs.quality_score for cs in summary.cluster_summaries)):
            
            # Primary sort: Quality Score (descending)
            # Secondary sort: Response Count (descending)
            sorted_clusters = sorted(
                summary.cluster_summaries,
                key=lambda cs: (
                    cs.quality_score.combined_score if cs.quality_score else 0,
                    cs.response_count
                ),
                reverse=True
            )
        else:
            # Default: Response Count (descending)
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
            # Recommended actions and caveats
            "recommended_actions": summary.recommended_actions or [],
            "caveats": summary.caveats or [],
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
        a {{
            color: #007bff;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
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
