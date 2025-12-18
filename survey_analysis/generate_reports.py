#!/usr/bin/env python3
"""
Generate Markdown reports from survey summaries.

This script converts JSON summaries into well-formatted Markdown documents.
"""

import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

from config import get_output_dir


def format_timestamp() -> str:
    """Get formatted timestamp."""
    return datetime.now().strftime("%Y年%m月%d日 %H:%M")


def generate_question_section(q_summary: Dict[str, Any], include_stats: bool = True) -> str:
    """Generate Markdown section for a single question."""
    md = ""
    
    # Question header
    question_id = q_summary.get('question_id', '')
    question = q_summary.get('question', '')
    topic = q_summary.get('topic', '')
    
    md += f"### {question_id}: {question}\n\n"
    
    if topic:
        md += f"**トピック**: {topic}\n\n"
    
    # Statistics
    if include_stats:
        num_responses = q_summary.get('num_responses', 0)
        md += f"**回答数**: {num_responses}件\n\n"
    
    # Summary
    summary = q_summary.get('summary', '要約なし')
    md += "#### 要約\n\n"
    md += f"{summary}\n\n"
    
    # Batch summaries (if available)
    batch_summaries = q_summary.get('batch_summaries', [])
    if batch_summaries and len(batch_summaries) > 1:
        md += "<details>\n"
        md += "<summary>バッチ要約詳細（クリックで展開）</summary>\n\n"
        for i, batch in enumerate(batch_summaries, 1):
            md += f"**バッチ {i}**:\n\n{batch}\n\n"
        md += "</details>\n\n"
    
    md += "---\n\n"
    
    return md


def generate_markdown_report(
    summary_file: Path,
    include_stats: bool = True,
    include_timestamp: bool = True
) -> str:
    """
    Generate Markdown report from summary JSON.
    
    Args:
        summary_file: Path to summary JSON file
        include_stats: Include statistics in report
        include_timestamp: Include generation timestamp
    
    Returns:
        Markdown content as string
    """
    # Load summary
    with open(summary_file, 'r', encoding='utf-8') as f:
        summary = json.load(f)
    
    md = ""
    
    # Title and metadata
    title = summary.get('title', 'アンケート要約')
    md += f"# {title}\n\n"
    
    description = summary.get('description', '')
    if description:
        md += f"{description}\n\n"
    
    md += "---\n\n"
    
    # Summary information
    md += "## 概要\n\n"
    
    slug = summary.get('slug', '')
    if slug:
        md += f"**スラッグ**: `{slug}`\n\n"
    
    if include_stats:
        num_sessions = summary.get('num_sessions', 0)
        num_questions = summary.get('num_questions', 0)
        md += f"- **セッション数**: {num_sessions}件\n"
        md += f"- **質問数**: {num_questions}問\n"
    
    provider = summary.get('provider', '')
    model = summary.get('model', '')
    if provider and model:
        md += f"- **要約生成**: {provider} ({model})\n"
    
    if include_timestamp:
        md += f"- **生成日時**: {format_timestamp()}\n"
    
    md += "\n---\n\n"
    
    # Table of Contents
    question_summaries = summary.get('question_summaries', [])
    
    if len(question_summaries) > 3:
        md += "## 目次\n\n"
        for q in question_summaries:
            q_id = q.get('question_id', '')
            q_text = q.get('question', '')[:50]
            anchor = q_id.lower().replace('_', '-')
            md += f"- [{q_id}: {q_text}...](#{anchor})\n"
        md += "\n---\n\n"
    
    # Question summaries
    md += "## 質問別要約\n\n"
    
    for q_summary in question_summaries:
        md += generate_question_section(q_summary, include_stats)
    
    # Footer
    md += "---\n\n"
    md += f"*このレポートは自動生成されました ({format_timestamp()})*\n"
    
    return md


def save_markdown_report(
    summary_file: Path,
    output_dir: Path,
    include_stats: bool = True,
    include_timestamp: bool = True
) -> Path:
    """
    Generate and save Markdown report.
    
    Returns:
        Path to saved Markdown file
    """
    # Generate Markdown
    md_content = generate_markdown_report(
        summary_file,
        include_stats,
        include_timestamp
    )
    
    # Determine output filename
    slug = summary_file.stem.replace('_summary', '')
    output_file = output_dir / f"{slug}.md"
    
    # Save
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(md_content)
    
    return output_file


def generate_index_page(
    summary_files: List[Path],
    output_dir: Path,
    provider_name: str
) -> Path:
    """
    Generate an index page linking to all survey reports.
    
    Returns:
        Path to index file
    """
    md = f"# アンケート要約レポート - {provider_name.upper()}\n\n"
    md += f"生成日時: {format_timestamp()}\n\n"
    md += "---\n\n"
    
    md += "## レポート一覧\n\n"
    
    for summary_file in sorted(summary_files):
        with open(summary_file, 'r', encoding='utf-8') as f:
            summary = json.load(f)
        
        title = summary.get('title', 'Untitled')
        slug = summary.get('slug', '')
        num_sessions = summary.get('num_sessions', 0)
        num_questions = summary.get('num_questions', 0)
        
        md_filename = summary_file.stem.replace('_summary', '') + '.md'
        
        md += f"### [{title}]({md_filename})\n\n"
        md += f"- **スラッグ**: `{slug}`\n"
        md += f"- **セッション数**: {num_sessions}件\n"
        md += f"- **質問数**: {num_questions}問\n\n"
    
    md += "---\n\n"
    md += f"*合計 {len(summary_files)} 件のアンケート*\n"
    
    # Save index
    index_file = output_dir / "index.md"
    with open(index_file, 'w', encoding='utf-8') as f:
        f.write(md)
    
    return index_file


def process_all_summaries(
    provider_name: str,
    include_stats: bool = True,
    include_timestamp: bool = True
):
    """
    Process all summary files for a given provider.
    
    Args:
        provider_name: Name of LLM provider ("claude" or "gemini")
        include_stats: Include statistics in reports
        include_timestamp: Include timestamps in reports
    """
    print("\n" + "="*70)
    print(f"MARKDOWN REPORT GENERATION - {provider_name.upper()}")
    print("="*70)
    
    # Get input/output directories
    output_dir = get_output_dir(provider_name)
    
    # Find summary files
    summary_files = sorted(output_dir.glob("*_summary.json"))
    
    if not summary_files:
        print(f"❌ No summary files found in {output_dir}")
        return
    
    print(f"\n📁 Found {len(summary_files)} summary file(s)")
    
    # Process each summary
    generated_files = []
    
    for summary_file in summary_files:
        try:
            md_file = save_markdown_report(
                summary_file,
                output_dir,
                include_stats,
                include_timestamp
            )
            generated_files.append(md_file)
            print(f"   ✅ {md_file.name}")
        except Exception as e:
            print(f"   ❌ Error processing {summary_file.name}: {e}")
    
    # Generate index page
    if generated_files:
        try:
            index_file = generate_index_page(summary_files, output_dir, provider_name)
            print(f"\n   📋 Index page: {index_file.name}")
        except Exception as e:
            print(f"   ❌ Error generating index: {e}")
    
    print("\n" + "="*70)
    print("REPORT GENERATION COMPLETE")
    print("="*70)
    print(f"Provider: {provider_name.upper()}")
    print(f"Reports generated: {len(generated_files)}")
    print(f"Output directory: {output_dir}")
    print("="*70 + "\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate Markdown reports from survey summaries"
    )
    parser.add_argument(
        '--llm',
        choices=['claude', 'gemini', 'both'],
        default='both',
        help='LLM provider to process'
    )
    parser.add_argument(
        '--no-stats',
        action='store_true',
        help='Exclude statistics from reports'
    )
    parser.add_argument(
        '--no-timestamp',
        action='store_true',
        help='Exclude timestamps from reports'
    )
    
    args = parser.parse_args()
    
    include_stats = not args.no_stats
    include_timestamp = not args.no_timestamp
    
    # Process selected provider(s)
    if args.llm in ['claude', 'both']:
        process_all_summaries('claude', include_stats, include_timestamp)
    
    if args.llm in ['gemini', 'both']:
        process_all_summaries('gemini', include_stats, include_timestamp)
    
    print("✨ All report generation complete!")


if __name__ == "__main__":
    main()



















