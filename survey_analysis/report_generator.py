#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Report Generator Module
分析結果のレポート生成（Markdown/HTML）
"""

from datetime import datetime
from typing import Dict, List, Any
from jinja2 import Template
import os


class ReportGenerator:
    """
    Generate analysis reports in various formats
    """
    
    def __init__(self):
        self.markdown_template = self._get_markdown_template()
        self.html_template = self._get_html_template()
    
    def _get_markdown_template(self) -> str:
        """Get Markdown report template"""
        return """# アンケート分析レポート: {{ survey_title }}

**生成日時**: {{ timestamp }}  
**総回答数**: {{ total_responses }}件

---

## エグゼクティブサマリー

{{ summary }}

---

## 重要キーワード Top {{ top_keywords|length }}

{% for keyword, score in top_keywords %}
{{ loop.index }}. **{{ keyword }}** (重要度: {{ "%.3f"|format(score) }})
{% endfor %}

---

## カテゴリ別分析

{% for category_name, category_data in categories.items() %}
### {{ category_name }} ({{ category_data.count }}件, {{ "%.1f"|format(category_data.percentage) }}%)

**感情分析**:
- 肯定的: {{ category_data.sentiment.positive }}件 ({{ "%.1f"|format(category_data.sentiment.positive_pct) }}%)
- 否定的: {{ category_data.sentiment.negative }}件 ({{ "%.1f"|format(category_data.sentiment.negative_pct) }}%)
- 中立: {{ category_data.sentiment.neutral }}件 ({{ "%.1f"|format(category_data.sentiment.neutral_pct) }}%)

**意図分析**:
- 要望・希望: {{ category_data.intent.desire_count }}件
- 懸念・心配: {{ category_data.intent.concern_count }}件
- 提案: {{ category_data.intent.proposal_count }}件

**代表的な回答**:
{% for response in category_data.sample_responses %}
{{ loop.index }}. {{ response }}
{% endfor %}

{% if category_data.keywords %}
**このカテゴリの特徴的なキーワード**: {{ category_data.keywords|join(', ') }}
{% endif %}

---

{% endfor %}

## インサイト

### 主要な発見

{% for insight in insights %}
- {{ insight }}
{% endfor %}

### 回答者の主な関心事

{% for topic, count in top_topics %}
- **{{ topic }}**: {{ count }}件の回答で言及
{% endfor %}

---

## 推奨アクション

{% for action in recommended_actions %}
{{ loop.index }}. {{ action }}
{% endfor %}

---

*このレポートは自動生成されました。*
"""
    
    def _get_html_template(self) -> str:
        """Get HTML report template"""
        return """<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>アンケート分析レポート: {{ survey_title }}</title>
    <style>
        body {
            font-family: 'Hiragino Sans', 'Yu Gothic', 'Meiryo', sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background-color: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }
        h2 {
            color: #34495e;
            margin-top: 30px;
            border-left: 4px solid #3498db;
            padding-left: 10px;
        }
        h3 {
            color: #555;
            margin-top: 20px;
        }
        .meta-info {
            color: #777;
            font-size: 0.9em;
            margin-bottom: 30px;
        }
        .summary {
            background-color: #e8f4f8;
            padding: 20px;
            border-radius: 5px;
            margin: 20px 0;
            border-left: 4px solid #3498db;
        }
        .category {
            margin: 30px 0;
            padding: 20px;
            background-color: #f9f9f9;
            border-radius: 5px;
            border: 1px solid #ddd;
        }
        .sentiment-bar {
            display: flex;
            height: 30px;
            margin: 10px 0;
            border-radius: 5px;
            overflow: hidden;
        }
        .positive {
            background-color: #2ecc71;
        }
        .negative {
            background-color: #e74c3c;
        }
        .neutral {
            background-color: #95a5a6;
        }
        .keyword-list {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin: 10px 0;
        }
        .keyword-tag {
            background-color: #3498db;
            color: white;
            padding: 5px 12px;
            border-radius: 15px;
            font-size: 0.9em;
        }
        .response-sample {
            background-color: white;
            padding: 15px;
            margin: 10px 0;
            border-left: 3px solid #3498db;
            border-radius: 3px;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        .stat-card {
            background-color: #ecf0f1;
            padding: 20px;
            border-radius: 5px;
            text-align: center;
        }
        .stat-number {
            font-size: 2em;
            font-weight: bold;
            color: #3498db;
        }
        .stat-label {
            color: #555;
            font-size: 0.9em;
            margin-top: 5px;
        }
        .insights {
            background-color: #fff3cd;
            padding: 20px;
            border-radius: 5px;
            border-left: 4px solid #ffc107;
            margin: 20px 0;
        }
        .actions {
            background-color: #d4edda;
            padding: 20px;
            border-radius: 5px;
            border-left: 4px solid #28a745;
            margin: 20px 0;
        }
        ul {
            padding-left: 20px;
        }
        li {
            margin: 8px 0;
        }
        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            text-align: center;
            color: #777;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>アンケート分析レポート: {{ survey_title }}</h1>
        
        <div class="meta-info">
            <strong>生成日時</strong>: {{ timestamp }}<br>
            <strong>総回答数</strong>: {{ total_responses }}件
        </div>
        
        <div class="summary">
            <h2>エグゼクティブサマリー</h2>
            <p>{{ summary }}</p>
        </div>
        
        <h2>重要キーワード Top {{ top_keywords|length }}</h2>
        <div class="keyword-list">
            {% for keyword, score in top_keywords %}
            <span class="keyword-tag">{{ keyword }}</span>
            {% endfor %}
        </div>
        
        <h2>カテゴリ別分析</h2>
        {% for category_name, category_data in categories.items() %}
        <div class="category">
            <h3>{{ category_name }}</h3>
            <p><strong>{{ category_data.count }}件</strong> (全体の{{ "%.1f"|format(category_data.percentage) }}%)</p>
            
            <h4>感情分析</h4>
            <div class="sentiment-bar">
                <div class="positive" style="width: {{ "%.1f"|format(category_data.sentiment.positive_pct) }}%;" 
                     title="肯定的: {{ category_data.sentiment.positive }}件"></div>
                <div class="neutral" style="width: {{ "%.1f"|format(category_data.sentiment.neutral_pct) }}%;" 
                     title="中立: {{ category_data.sentiment.neutral }}件"></div>
                <div class="negative" style="width: {{ "%.1f"|format(category_data.sentiment.negative_pct) }}%;" 
                     title="否定的: {{ category_data.sentiment.negative }}件"></div>
            </div>
            <p style="font-size: 0.9em; color: #555;">
                肯定的: {{ category_data.sentiment.positive }}件 ({{ "%.1f"|format(category_data.sentiment.positive_pct) }}%) | 
                中立: {{ category_data.sentiment.neutral }}件 ({{ "%.1f"|format(category_data.sentiment.neutral_pct) }}%) | 
                否定的: {{ category_data.sentiment.negative }}件 ({{ "%.1f"|format(category_data.sentiment.negative_pct) }}%)
            </p>
            
            <h4>意図分析</h4>
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-number">{{ category_data.intent.desire_count }}</div>
                    <div class="stat-label">要望・希望</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{{ category_data.intent.concern_count }}</div>
                    <div class="stat-label">懸念・心配</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{{ category_data.intent.proposal_count }}</div>
                    <div class="stat-label">提案</div>
                </div>
            </div>
            
            {% if category_data.keywords %}
            <h4>特徴的なキーワード</h4>
            <div class="keyword-list">
                {% for kw in category_data.keywords %}
                <span class="keyword-tag">{{ kw }}</span>
                {% endfor %}
            </div>
            {% endif %}
            
            <h4>代表的な回答</h4>
            {% for response in category_data.sample_responses %}
            <div class="response-sample">{{ response }}</div>
            {% endfor %}
        </div>
        {% endfor %}
        
        <div class="insights">
            <h2>インサイト</h2>
            <h3>主要な発見</h3>
            <ul>
                {% for insight in insights %}
                <li>{{ insight }}</li>
                {% endfor %}
            </ul>
            
            <h3>回答者の主な関心事</h3>
            <ul>
                {% for topic, count in top_topics %}
                <li><strong>{{ topic }}</strong>: {{ count }}件の回答で言及</li>
                {% endfor %}
            </ul>
        </div>
        
        <div class="actions">
            <h2>推奨アクション</h2>
            <ol>
                {% for action in recommended_actions %}
                <li>{{ action }}</li>
                {% endfor %}
            </ol>
        </div>
        
        <div class="footer">
            このレポートは自動生成されました。
        </div>
    </div>
</body>
</html>
"""
    
    def generate_markdown_report(
        self,
        survey_title: str,
        analysis_data: Dict[str, Any],
        output_path: str
    ) -> str:
        """
        Generate Markdown format report
        
        Args:
            survey_title: Survey title
            analysis_data: Analysis data dictionary
            output_path: Output file path
            
        Returns:
            Path to generated report
        """
        template = Template(self.markdown_template)
        
        # Prepare data for template
        data = self._prepare_report_data(survey_title, analysis_data)
        
        # Render template
        content = template.render(**data)
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return output_path
    
    def generate_html_report(
        self,
        survey_title: str,
        analysis_data: Dict[str, Any],
        output_path: str
    ) -> str:
        """
        Generate HTML format report
        
        Args:
            survey_title: Survey title
            analysis_data: Analysis data dictionary
            output_path: Output file path
            
        Returns:
            Path to generated report
        """
        template = Template(self.html_template)
        
        # Prepare data for template
        data = self._prepare_report_data(survey_title, analysis_data)
        
        # Render template
        content = template.render(**data)
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return output_path
    
    def _prepare_report_data(
        self,
        survey_title: str,
        analysis_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare data for report template"""
        
        total_responses = analysis_data.get('total_responses', 0)
        
        # Prepare category data
        categories = {}
        for category_name, category_info in analysis_data.get('categories', {}).items():
            sentiment = category_info.get('sentiment', {})
            intent = category_info.get('intent', {})
            count = category_info.get('count', 0)
            
            categories[category_name] = {
                'count': count,
                'percentage': (count / total_responses * 100) if total_responses > 0 else 0,
                'sentiment': {
                    'positive': sentiment.get('positive', 0),
                    'negative': sentiment.get('negative', 0),
                    'neutral': sentiment.get('neutral', 0),
                    'positive_pct': sentiment.get('positive_pct', 0),
                    'negative_pct': sentiment.get('negative_pct', 0),
                    'neutral_pct': sentiment.get('neutral_pct', 0),
                },
                'intent': {
                    'desire_count': intent.get('desire_count', 0),
                    'concern_count': intent.get('concern_count', 0),
                    'proposal_count': intent.get('proposal_count', 0),
                },
                'sample_responses': category_info.get('sample_responses', []),
                'keywords': category_info.get('keywords', []),
            }
        
        # Generate insights
        insights = self._generate_insights(analysis_data)
        
        # Generate recommended actions
        actions = self._generate_actions(analysis_data)
        
        return {
            'survey_title': survey_title,
            'timestamp': datetime.now().strftime('%Y年%m月%d日 %H:%M:%S'),
            'total_responses': total_responses,
            'summary': analysis_data.get('summary', 'このアンケートの分析結果です。'),
            'top_keywords': analysis_data.get('top_keywords', [])[:10],
            'categories': categories,
            'insights': insights,
            'top_topics': analysis_data.get('top_topics', [])[:5],
            'recommended_actions': actions,
        }
    
    def _generate_insights(self, analysis_data: Dict[str, Any]) -> List[str]:
        """Generate insights from analysis data"""
        insights = []
        
        total = analysis_data.get('total_responses', 0)
        categories = analysis_data.get('categories', {})
        
        if not categories:
            return ['十分なデータがありません。']
        
        # Find largest category
        largest_category = max(categories.items(), key=lambda x: x[1].get('count', 0))
        largest_pct = (largest_category[1].get('count', 0) / total * 100) if total > 0 else 0
        insights.append(
            f"最も多い回答カテゴリは「{largest_category[0]}」で、全体の{largest_pct:.1f}%を占めています。"
        )
        
        # Sentiment analysis
        all_positive = sum(cat.get('sentiment', {}).get('positive', 0) for cat in categories.values())
        all_negative = sum(cat.get('sentiment', {}).get('negative', 0) for cat in categories.values())
        
        if all_positive > all_negative * 1.5:
            insights.append(f"全体的に肯定的な意見が多く（{all_positive}件）、好意的な反応が見られます。")
        elif all_negative > all_positive * 1.5:
            insights.append(f"懸念や否定的な意見が多く（{all_negative}件）、慎重な対応が求められます。")
        else:
            insights.append("肯定的な意見と否定的な意見がバランスよく分布しています。")
        
        # Intent analysis
        all_desires = sum(cat.get('intent', {}).get('desire_count', 0) for cat in categories.values())
        all_concerns = sum(cat.get('intent', {}).get('concern_count', 0) for cat in categories.values())
        
        if all_desires > 0:
            insights.append(f"回答者からの要望や期待が{all_desires}件寄せられています。")
        if all_concerns > 0:
            insights.append(f"{all_concerns}件の懸念事項が示されており、対応が必要です。")
        
        return insights
    
    def _generate_actions(self, analysis_data: Dict[str, Any]) -> List[str]:
        """Generate recommended actions from analysis data"""
        actions = []
        
        categories = analysis_data.get('categories', {})
        
        # Find categories with high concern
        for category_name, category_info in categories.items():
            concern_count = category_info.get('intent', {}).get('concern_count', 0)
            if concern_count > 2:
                actions.append(f"「{category_name}」カテゴリの懸念事項（{concern_count}件）に対する対応策を検討する")
        
        # Find categories with high desire
        for category_name, category_info in categories.items():
            desire_count = category_info.get('intent', {}).get('desire_count', 0)
            if desire_count > 2:
                actions.append(f"「{category_name}」カテゴリの要望（{desire_count}件）を施策に反映する")
        
        # General actions
        if not actions:
            actions.append("各カテゴリの代表的な意見を詳しく分析する")
            actions.append("回答者のニーズに基づいて優先順位を決定する")
        
        actions.append("定期的にアンケートを実施し、変化を追跡する")
        
        return actions


def test_report_generator():
    """Test function for report generator"""
    
    # Create sample analysis data
    sample_data = {
        'total_responses': 100,
        'summary': 'このアンケートでは政治の透明性とDX推進について多くの意見が寄せられました。',
        'top_keywords': [
            ('透明性', 0.85),
            ('政治', 0.72),
            ('DX', 0.68),
            ('改革', 0.55),
        ],
        'categories': {
            '政治の透明性': {
                'count': 45,
                'sentiment': {
                    'positive': 30,
                    'negative': 10,
                    'neutral': 5,
                    'positive_pct': 66.7,
                    'negative_pct': 22.2,
                    'neutral_pct': 11.1,
                },
                'intent': {
                    'desire_count': 20,
                    'concern_count': 5,
                    'proposal_count': 15,
                },
                'sample_responses': [
                    '政治資金の完全公開を実現してほしい',
                    '透明性の向上は民主主義の基本です',
                    '情報公開をもっと進めるべきだと思います',
                ],
                'keywords': ['透明性', '公開', '情報'],
            },
            'DX推進': {
                'count': 35,
                'sentiment': {
                    'positive': 25,
                    'negative': 5,
                    'neutral': 5,
                    'positive_pct': 71.4,
                    'negative_pct': 14.3,
                    'neutral_pct': 14.3,
                },
                'intent': {
                    'desire_count': 15,
                    'concern_count': 3,
                    'proposal_count': 10,
                },
                'sample_responses': [
                    'デジタル化をもっと進めてほしい',
                    'オンライン投票の実現に期待',
                ],
                'keywords': ['DX', 'デジタル', 'オンライン'],
            },
        },
        'top_topics': [
            ('政治', 60),
            ('透明性', 45),
            ('DX', 35),
        ],
    }
    
    generator = ReportGenerator()
    
    # Generate reports
    output_dir = '/Users/masa/forback/github/mirai_DB_backup/survey_analysis'
    os.makedirs(output_dir, exist_ok=True)
    
    md_path = os.path.join(output_dir, 'test_report.md')
    html_path = os.path.join(output_dir, 'test_report.html')
    
    generator.generate_markdown_report('テストアンケート', sample_data, md_path)
    generator.generate_html_report('テストアンケート', sample_data, html_path)
    
    print(f"Generated Markdown report: {md_path}")
    print(f"Generated HTML report: {html_path}")


if __name__ == '__main__':
    test_report_generator()





















