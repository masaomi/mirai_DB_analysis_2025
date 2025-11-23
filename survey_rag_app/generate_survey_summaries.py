#!/usr/bin/env python3
"""
Survey Summary Generator
Generates HTML summaries for each survey topic using RAG and LLM.
"""

import os
import json
import argparse
from datetime import datetime
from typing import List, Dict, Optional
from collections import Counter
from pathlib import Path

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_community.chat_models import ChatOllama
from langchain_aws import ChatBedrock
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from tqdm import tqdm
import boto3

# Configuration
CHROMA_DB_DIR = "./chroma_db"
COLLECTION_NAME = "survey_responses"
EMBEDDING_MODEL = "intfloat/multilingual-e5-base"
STATISTICS_FILE = "./ingestion_statistics.json"
OUTPUT_DIR = "./survey_summaries_html"

# Default LLM settings
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "gpt-oss:20b"
DEFAULT_BEDROCK_REGION = "us-east-1"
DEFAULT_BEDROCK_MODEL = "anthropic.claude-3-5-sonnet-20240620-v1:0"


def load_statistics() -> Optional[Dict]:
    """Load ingestion statistics from JSON file."""
    if os.path.exists(STATISTICS_FILE):
        try:
            with open(STATISTICS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  Warning: Failed to load statistics: {e}")
    return None


def get_vectorstore():
    """Initialize and return the vector store."""
    if not os.path.exists(CHROMA_DB_DIR):
        raise FileNotFoundError(f"ChromaDB not found at {CHROMA_DB_DIR}. Please run ingest_data.py first.")
    
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    return Chroma(
        persist_directory=CHROMA_DB_DIR,
        embedding_function=embeddings,
        collection_name=COLLECTION_NAME
    )


def get_llm(provider: str, **kwargs):
    """Initialize and return the LLM based on provider."""
    if provider == "ollama":
        base_url = kwargs.get("base_url", DEFAULT_OLLAMA_BASE_URL)
        model = kwargs.get("model", DEFAULT_OLLAMA_MODEL)
        print(f"Using Ollama: {model} at {base_url}")
        return ChatOllama(
            base_url=base_url,
            model=model,
            temperature=0.3
        )
    elif provider == "bedrock":
        region = kwargs.get("region", DEFAULT_BEDROCK_REGION)
        model_id = kwargs.get("model_id", DEFAULT_BEDROCK_MODEL)
        profile = kwargs.get("profile")
        
        print(f"Using AWS Bedrock: {model_id} in {region}")
        
        if profile:
            session = boto3.Session(profile_name=profile, region_name=region)
            client = session.client("bedrock-runtime")
        else:
            client = boto3.client("bedrock-runtime", region_name=region)
        
        return ChatBedrock(
            client=client,
            model_id=model_id,
            model_kwargs={"temperature": 0.3, "max_tokens": 4000}
        )
    else:
        raise ValueError(f"Unknown provider: {provider}")


def get_all_topics(vectorstore) -> List[tuple]:
    """
    Get all unique topics from the vector store.
    Returns list of (topic_name, topic_slug) tuples.
    """
    print("Retrieving all topics from database...")
    
    # Get a sample of documents to extract topics
    # We'll use a dummy query to get documents
    results = vectorstore.similarity_search("", k=10000)
    
    topics = {}
    for doc in results:
        topic = doc.metadata.get("topic", "Unknown")
        topic_slug = doc.metadata.get("topic_slug", "unknown")
        if topic not in topics:
            topics[topic] = topic_slug
    
    topic_list = [(name, slug) for name, slug in topics.items()]
    print(f"Found {len(topic_list)} unique topics")
    return topic_list


def get_topic_documents(vectorstore, topic_slug: str, max_docs: int = 100) -> List:
    """
    Get documents for a specific topic.
    Returns up to max_docs documents.
    """
    # Use the metadata filtering capabilities of ChromaDB
    results = vectorstore.similarity_search(
        "",  # Empty query to get all
        k=max_docs,
        filter={"topic_slug": topic_slug}
    )
    return results


def analyze_topic_data(docs: List) -> Dict:
    """Analyze documents and return statistics."""
    if not docs:
        return {}
    
    # Basic stats
    total_responses = len(docs)
    
    # Sentiment analysis
    sentiments = [doc.metadata.get("sentiment_label", "unknown") for doc in docs]
    sentiment_counts = Counter(sentiments)
    sentiment_scores = [doc.metadata.get("sentiment_score", 0) for doc in docs]
    avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
    
    # Quality analysis
    qualities = [doc.metadata.get("response_quality", "unknown") for doc in docs]
    quality_counts = Counter(qualities)
    
    # Date range
    dates = [doc.metadata.get("date", "") for doc in docs if doc.metadata.get("date")]
    date_range = {
        "start": min(dates) if dates else "unknown",
        "end": max(dates) if dates else "unknown"
    }
    
    # Keyword analysis
    positive_count = sum(1 for doc in docs if doc.metadata.get("has_positive_keywords", False))
    negative_count = sum(1 for doc in docs if doc.metadata.get("has_negative_keywords", False))
    policy_count = sum(1 for doc in docs if doc.metadata.get("has_policy_keywords", False))
    
    # Question types
    question_types = [doc.metadata.get("question_type", "unknown") for doc in docs]
    question_type_counts = Counter(question_types)
    
    return {
        "total_responses": total_responses,
        "sentiment_distribution": dict(sentiment_counts),
        "average_sentiment": round(avg_sentiment, 3),
        "quality_distribution": dict(quality_counts),
        "date_range": date_range,
        "keyword_stats": {
            "positive": positive_count,
            "negative": negative_count,
            "policy": policy_count
        },
        "question_type_distribution": dict(question_type_counts)
    }


def format_docs_for_summary(docs: List, max_examples: int = 30) -> str:
    """Format documents for LLM summary."""
    formatted = []
    
    # Take a sample of documents
    sample_docs = docs[:max_examples]
    
    for i, doc in enumerate(sample_docs, 1):
        question = doc.metadata.get("question", "不明")
        answer = doc.metadata.get("answer", doc.page_content)
        date = doc.metadata.get("date", "不明")
        sentiment = doc.metadata.get("sentiment_label", "不明")
        
        formatted.append(
            f"【回答 {i}】\n"
            f"日付: {date}\n"
            f"質問: {question}\n"
            f"回答: {answer}\n"
            f"感情: {sentiment}\n"
        )
    
    if len(docs) > max_examples:
        formatted.append(f"\n... 他 {len(docs) - max_examples} 件の回答")
    
    return "\n".join(formatted)


def generate_summary(llm, topic_name: str, docs: List, stats: Dict) -> str:
    """Generate summary using LLM."""
    
    # Format documents
    context = format_docs_for_summary(docs, max_examples=30)
    
    # Create prompt
    template = """あなたはアンケート調査の分析専門家です。以下のアンケート調査「{topic_name}」の回答を分析し、包括的な要約レポートを作成してください。

【データ統計】
- 総回答数: {total_responses}件
- 平均感情スコア: {avg_sentiment} (-1: ネガティブ, 0: 中立, +1: ポジティブ)
- 期間: {date_start} 〜 {date_end}
- ポジティブキーワード含有: {positive_count}件
- ネガティブキーワード含有: {negative_count}件

【実際の回答サンプル（最大30件）】
{context}

【要約レポート作成指示】
以下の構成で、マークダウン形式で要約を作成してください：

1. **概要サマリー**（2-3段落）
   - このアンケートの主要な目的と背景
   - 全体的な傾向と回答の特徴

2. **主要な発見事項**（箇条書き）
   - 最も重要な3-5つの発見
   - 具体的な回答例を引用

3. **感情分析**
   - 回答者の全体的な感情傾向
   - ポジティブ・ネガティブ意見の内訳

4. **主要な意見・テーマ**
   - 繰り返し現れるテーマやトピック
   - 代表的な意見グループ

5. **注目すべき個別意見**
   - 特に印象的だった回答
   - ユニークな視点や提案

6. **結論と示唆**
   - データから得られる洞察
   - 今後の対応や検討事項の提案

できるだけ具体的に、実際の回答を引用しながら分析してください。"""

    prompt = PromptTemplate.from_template(template)
    
    chain = prompt | llm | StrOutputParser()
    
    try:
        result = chain.invoke({
            "topic_name": topic_name,
            "total_responses": stats.get("total_responses", 0),
            "avg_sentiment": stats.get("average_sentiment", 0),
            "date_start": stats.get("date_range", {}).get("start", "不明"),
            "date_end": stats.get("date_range", {}).get("end", "不明"),
            "positive_count": stats.get("keyword_stats", {}).get("positive", 0),
            "negative_count": stats.get("keyword_stats", {}).get("negative", 0),
            "context": context
        })
        return result
    except Exception as e:
        return f"エラー: 要約生成中に問題が発生しました。\n{str(e)}"


def convert_markdown_to_html(markdown_text: str) -> str:
    """Convert markdown to HTML (improved conversion)."""
    import re
    
    lines = markdown_text.split('\n')
    html_lines = []
    in_list = False
    in_table = False
    in_paragraph = False
    
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # Empty lines
        if not stripped:
            if in_paragraph:
                html_lines.append('</p>')
                in_paragraph = False
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            i += 1
            continue
        
        # Headers
        if stripped.startswith('#### '):
            if in_paragraph:
                html_lines.append('</p>')
                in_paragraph = False
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            html_lines.append(f'<h4>{stripped[5:]}</h4>')
        elif stripped.startswith('### '):
            if in_paragraph:
                html_lines.append('</p>')
                in_paragraph = False
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            html_lines.append(f'<h3>{stripped[4:]}</h3>')
        elif stripped.startswith('## '):
            if in_paragraph:
                html_lines.append('</p>')
                in_paragraph = False
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            html_lines.append(f'<h2>{stripped[3:]}</h2>')
        elif stripped.startswith('# '):
            if in_paragraph:
                html_lines.append('</p>')
                in_paragraph = False
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            html_lines.append(f'<h2>{stripped[2:]}</h2>')  # Use h2 for main sections
        
        # Lists
        elif stripped.startswith('- ') or stripped.startswith('* '):
            if in_paragraph:
                html_lines.append('</p>')
                in_paragraph = False
            if not in_list:
                html_lines.append('<ul>')
                in_list = True
            # Process bold and italic in list items
            item_text = stripped[2:]
            item_text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', item_text)
            item_text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', item_text)
            html_lines.append(f'<li>{item_text}</li>')
        
        # Tables
        elif '|' in stripped and not in_table:
            if in_paragraph:
                html_lines.append('</p>')
                in_paragraph = False
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            
            # Start table
            html_lines.append('<table>')
            html_lines.append('<thead><tr>')
            
            # Header row
            cells = [cell.strip() for cell in stripped.split('|') if cell.strip()]
            for cell in cells:
                cell_text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', cell)
                html_lines.append(f'<th>{cell_text}</th>')
            html_lines.append('</tr></thead>')
            html_lines.append('<tbody>')
            
            # Skip separator line
            i += 1
            if i < len(lines) and '|' in lines[i] and '-' in lines[i]:
                i += 1
            
            # Process table rows
            while i < len(lines) and '|' in lines[i]:
                row = lines[i].strip()
                if row:
                    html_lines.append('<tr>')
                    cells = [cell.strip() for cell in row.split('|') if cell.strip()]
                    for cell in cells:
                        cell_text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', cell)
                        html_lines.append(f'<td>{cell_text}</td>')
                    html_lines.append('</tr>')
                i += 1
            
            html_lines.append('</tbody></table>')
            continue
        
        # Regular paragraphs
        else:
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            if not in_paragraph:
                html_lines.append('<p>')
                in_paragraph = True
            
            # Process bold and italic
            text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', stripped)
            text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
            html_lines.append(text)
        
        i += 1
    
    # Close any open tags
    if in_paragraph:
        html_lines.append('</p>')
    if in_list:
        html_lines.append('</ul>')
    
    return '\n'.join(html_lines)


def generate_html_report(topic_name: str, topic_slug: str, summary: str, stats: Dict, metadata: Dict) -> str:
    """Generate complete HTML report."""
    
    # Convert markdown summary to HTML
    summary_html = convert_markdown_to_html(summary)
    
    # Build statistics HTML
    stats_html = f"""
    <div class="statistics">
        <h2>📊 統計情報</h2>
        <div class="stats-grid">
            <div class="stat-card">
                <h3>総回答数</h3>
                <p class="stat-value">{stats.get('total_responses', 0):,}</p>
            </div>
            <div class="stat-card">
                <h3>平均感情スコア</h3>
                <p class="stat-value">{stats.get('average_sentiment', 0):.3f}</p>
                <p class="stat-label">(-1: ネガティブ 〜 +1: ポジティブ)</p>
            </div>
            <div class="stat-card">
                <h3>期間</h3>
                <p class="stat-value">{stats.get('date_range', {}).get('start', '不明')}</p>
                <p class="stat-label">〜 {stats.get('date_range', {}).get('end', '不明')}</p>
            </div>
        </div>
        
        <h3>感情分布</h3>
        <table>
            <tr>
                <th>感情</th>
                <th>回答数</th>
                <th>割合</th>
            </tr>
    """
    
    total = stats.get('total_responses', 1)
    for sentiment, count in stats.get('sentiment_distribution', {}).items():
        percentage = (count / total) * 100 if total > 0 else 0
        stats_html += f"""
            <tr>
                <td>{sentiment}</td>
                <td>{count:,}</td>
                <td>{percentage:.1f}%</td>
            </tr>
        """
    
    stats_html += """
        </table>
        
        <h3>品質分布</h3>
        <table>
            <tr>
                <th>品質</th>
                <th>回答数</th>
                <th>割合</th>
            </tr>
    """
    
    for quality, count in stats.get('quality_distribution', {}).items():
        percentage = (count / total) * 100 if total > 0 else 0
        stats_html += f"""
            <tr>
                <td>{quality}</td>
                <td>{count:,}</td>
                <td>{percentage:.1f}%</td>
            </tr>
        """
    
    stats_html += """
        </table>
        
        <h3>キーワード統計</h3>
        <table>
            <tr>
                <th>種類</th>
                <th>該当回答数</th>
            </tr>
    """
    
    keyword_stats = stats.get('keyword_stats', {})
    stats_html += f"""
            <tr>
                <td>ポジティブキーワード</td>
                <td>{keyword_stats.get('positive', 0):,}</td>
            </tr>
            <tr>
                <td>ネガティブキーワード</td>
                <td>{keyword_stats.get('negative', 0):,}</td>
            </tr>
            <tr>
                <td>政策関連キーワード</td>
                <td>{keyword_stats.get('policy', 0):,}</td>
            </tr>
        </table>
    </div>
    """
    
    # Complete HTML
    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{topic_name} - アンケート要約レポート</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .header h1 {{
            margin: 0 0 10px 0;
            font-size: 2em;
        }}
        .metadata {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .metadata p {{
            margin: 5px 0;
            color: #666;
        }}
        .summary {{
            background: white;
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .summary h1 {{
            color: #667eea;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }}
        .summary h2 {{
            color: #764ba2;
            margin-top: 30px;
        }}
        .summary h3 {{
            color: #555;
        }}
        .summary ul {{
            padding-left: 25px;
        }}
        .summary li {{
            margin: 10px 0;
        }}
        .summary table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        .summary th, .summary td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        .summary th {{
            background-color: #f0f0f0;
            color: #333;
            font-weight: bold;
        }}
        .summary tr:hover {{
            background-color: #f9f9f9;
        }}
        .summary p {{
            margin: 15px 0;
        }}
        .summary em {{
            font-style: italic;
            color: #555;
        }}
        .statistics {{
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .statistics h2 {{
            color: #667eea;
            margin-top: 0;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .stat-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }}
        .stat-card h3 {{
            margin: 0 0 10px 0;
            color: #666;
            font-size: 0.9em;
            text-transform: uppercase;
        }}
        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
            margin: 0;
        }}
        .stat-label {{
            font-size: 0.85em;
            color: #999;
            margin: 5px 0 0 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #667eea;
            color: white;
            font-weight: bold;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .footer {{
            text-align: center;
            color: #999;
            padding: 20px;
            font-size: 0.9em;
        }}
        @media print {{
            body {{
                background: white;
            }}
            .header, .metadata, .summary, .statistics {{
                box-shadow: none;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{topic_name}</h1>
        <p>アンケート要約レポート</p>
    </div>
    
    <div class="metadata">
        <p><strong>トピックID:</strong> {topic_slug}</p>
        <p><strong>生成日時:</strong> {metadata.get('generated_at', '')}</p>
        <p><strong>LLMプロバイダー:</strong> {metadata.get('llm_provider', '')}</p>
        <p><strong>総回答数:</strong> {stats.get('total_responses', 0):,}件</p>
    </div>
    
    <div class="summary">
        <h1>📝 要約レポート</h1>
        {summary_html}
    </div>
    
    {stats_html}
    
    <div class="footer">
        <p>Generated by Survey RAG Analysis System</p>
        <p>{metadata.get('generated_at', '')}</p>
    </div>
</body>
</html>
"""
    
    return html


def main():
    parser = argparse.ArgumentParser(
        description="Generate HTML summaries for each survey topic using RAG and LLM"
    )
    parser.add_argument(
        "--provider",
        choices=["ollama", "bedrock"],
        default="ollama",
        help="LLM provider (default: ollama)"
    )
    parser.add_argument(
        "--ollama-base-url",
        default=DEFAULT_OLLAMA_BASE_URL,
        help=f"Ollama base URL (default: {DEFAULT_OLLAMA_BASE_URL})"
    )
    parser.add_argument(
        "--ollama-model",
        default=DEFAULT_OLLAMA_MODEL,
        help=f"Ollama model name (default: {DEFAULT_OLLAMA_MODEL})"
    )
    parser.add_argument(
        "--bedrock-region",
        default=DEFAULT_BEDROCK_REGION,
        help=f"AWS Bedrock region (default: {DEFAULT_BEDROCK_REGION})"
    )
    parser.add_argument(
        "--bedrock-model",
        default=DEFAULT_BEDROCK_MODEL,
        help=f"AWS Bedrock model ID (default: {DEFAULT_BEDROCK_MODEL})"
    )
    parser.add_argument(
        "--bedrock-profile",
        help="AWS profile name (optional)"
    )
    parser.add_argument(
        "--output-dir",
        default=OUTPUT_DIR,
        help=f"Output directory for HTML files (default: {OUTPUT_DIR})"
    )
    parser.add_argument(
        "--max-docs",
        type=int,
        default=100,
        help="Maximum documents per topic to analyze (default: 100)"
    )
    parser.add_argument(
        "--topics",
        nargs="+",
        help="Specific topic slugs to process (optional, processes all if not specified)"
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("Survey Summary Generator")
    print("="*60 + "\n")
    
    # Create output directory
    output_path = Path(args.output_dir)
    output_path.mkdir(exist_ok=True)
    print(f"📁 Output directory: {output_path.absolute()}\n")
    
    # Initialize vector store
    print("🔧 Initializing vector store...")
    try:
        vectorstore = get_vectorstore()
        print("✅ Vector store loaded\n")
    except Exception as e:
        print(f"❌ Error loading vector store: {e}")
        return
    
    # Initialize LLM
    print("🤖 Initializing LLM...")
    try:
        llm_kwargs = {}
        if args.provider == "ollama":
            llm_kwargs = {
                "base_url": args.ollama_base_url,
                "model": args.ollama_model
            }
        else:  # bedrock
            llm_kwargs = {
                "region": args.bedrock_region,
                "model_id": args.bedrock_model,
                "profile": args.bedrock_profile
            }
        
        llm = get_llm(args.provider, **llm_kwargs)
        print("✅ LLM initialized\n")
    except Exception as e:
        print(f"❌ Error initializing LLM: {e}")
        return
    
    # Get topics
    print("📋 Retrieving topics...")
    try:
        all_topics = get_all_topics(vectorstore)
        
        # Filter topics if specified
        if args.topics:
            all_topics = [(name, slug) for name, slug in all_topics if slug in args.topics]
            print(f"✅ Found {len(all_topics)} matching topics\n")
        else:
            print(f"✅ Found {len(all_topics)} topics\n")
        
        if not all_topics:
            print("❌ No topics found")
            return
            
    except Exception as e:
        print(f"❌ Error retrieving topics: {e}")
        return
    
    # Process each topic
    print("🚀 Generating summaries...\n")
    
    metadata_list = []
    
    for topic_name, topic_slug in tqdm(all_topics, desc="Processing topics"):
        try:
            print(f"\n📊 Processing: {topic_name}")
            
            # Get documents for this topic
            docs = get_topic_documents(vectorstore, topic_slug, max_docs=args.max_docs)
            
            if not docs:
                print(f"  ⚠️  No documents found for {topic_name}")
                continue
            
            print(f"  📄 Retrieved {len(docs)} documents")
            
            # Analyze data
            stats = analyze_topic_data(docs)
            print(f"  📈 Analyzed statistics")
            
            # Generate summary
            print(f"  🤖 Generating summary with LLM...")
            summary = generate_summary(llm, topic_name, docs, stats)
            print(f"  ✅ Summary generated")
            
            # Generate HTML
            metadata = {
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "llm_provider": f"{args.provider} ({args.ollama_model if args.provider == 'ollama' else args.bedrock_model})",
                "topic_name": topic_name,
                "topic_slug": topic_slug,
                "total_responses": stats.get("total_responses", 0)
            }
            
            html = generate_html_report(topic_name, topic_slug, summary, stats, metadata)
            
            # Save HTML file
            filename = f"{topic_slug}.html"
            filepath = output_path / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html)
            
            print(f"  💾 Saved: {filename}")
            
            metadata_list.append(metadata)
            
        except Exception as e:
            print(f"  ❌ Error processing {topic_name}: {e}")
            continue
    
    # Generate index HTML
    print("\n📑 Generating index file...")
    index_html = generate_index_html(metadata_list, args)
    index_path = output_path / "index.html"
    
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(index_html)
    
    print(f"💾 Saved: index.html")
    
    print("\n" + "="*60)
    print("✅ Summary generation complete!")
    print("="*60)
    print(f"\n📁 Output directory: {output_path.absolute()}")
    print(f"📊 Generated {len(metadata_list)} HTML summaries")
    print(f"🌐 Open index.html in a browser to view all summaries\n")


def generate_index_html(metadata_list: List[Dict], args) -> str:
    """Generate index HTML with links to all summaries."""
    
    # Sort by total responses (descending)
    sorted_metadata = sorted(metadata_list, key=lambda x: x.get('total_responses', 0), reverse=True)
    
    # Generate list items
    list_items = ""
    for meta in sorted_metadata:
        list_items += f"""
        <div class="survey-card">
            <h3><a href="{meta['topic_slug']}.html">{meta['topic_name']}</a></h3>
            <p class="survey-meta">
                <span class="badge">回答数: {meta['total_responses']:,}</span>
                <span class="badge">生成日時: {meta['generated_at']}</span>
            </p>
        </div>
        """
    
    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>アンケート要約レポート一覧</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .header h1 {{
            margin: 0 0 10px 0;
            font-size: 2.5em;
        }}
        .info {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .survey-card {{
            background: white;
            padding: 25px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .survey-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }}
        .survey-card h3 {{
            margin: 0 0 10px 0;
        }}
        .survey-card h3 a {{
            color: #667eea;
            text-decoration: none;
        }}
        .survey-card h3 a:hover {{
            text-decoration: underline;
        }}
        .survey-meta {{
            color: #666;
            font-size: 0.9em;
        }}
        .badge {{
            display: inline-block;
            background: #f0f0f0;
            padding: 5px 10px;
            border-radius: 5px;
            margin-right: 10px;
        }}
        .footer {{
            text-align: center;
            color: #999;
            padding: 20px;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 アンケート要約レポート一覧</h1>
        <p>Survey RAG Analysis System</p>
    </div>
    
    <div class="info">
        <p><strong>生成日時:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        <p><strong>LLMプロバイダー:</strong> {args.provider}</p>
        <p><strong>総レポート数:</strong> {len(metadata_list)}</p>
        <p><strong>総回答数:</strong> {sum(m.get('total_responses', 0) for m in metadata_list):,}</p>
    </div>
    
    <div class="surveys">
        {list_items}
    </div>
    
    <div class="footer">
        <p>Generated by Survey RAG Analysis System</p>
        <p>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
    </div>
</body>
</html>
"""
    
    return html


if __name__ == "__main__":
    main()

