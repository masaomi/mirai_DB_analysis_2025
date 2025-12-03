#!/usr/bin/env python3
"""
Summarize survey responses using LLMs.

This script processes survey chunks and generates summaries for each
question using Claude Sonnet 4.5 or Gemini 3 Pro.
"""

import json
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
from collections import defaultdict
from tqdm import tqdm

from config import (
    SURVEY_CHUNKS_DIR,
    get_output_dir,
    DEFAULT_BATCH_SIZE,
    SUMMARY_MAX_TOKENS,
    SUMMARY_TEMPERATURE,
)
from llm_providers import get_provider, LLMProvider
from smart_splitter import (
    should_split_question,
    split_qa_data,
    estimate_chunk_tokens,
    calculate_optimal_chunk_size
)


def load_survey_chunk(file_path: Path) -> dict:
    """Load a survey chunk JSON file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_qa_pairs(survey_data: dict) -> Dict[str, List[Dict[str, str]]]:
    """
    Extract question-answer pairs from survey data.
    
    Returns:
        Dict mapping question_id to list of {question, answer, session_id}
    """
    qa_pairs = defaultdict(list)
    
    config = survey_data.get('config', {})
    questions = config.get('questions', [])
    
    # Create question lookup
    question_map = {}
    for q in questions:
        q_id = q.get('id')
        q_text = q.get('text') or q.get('mainQuestion', '')
        q_topic = q.get('topic', '')
        question_map[q_id] = {
            'id': q_id,
            'text': q_text,
            'topic': q_topic
        }
    
    # Extract answers from sessions
    sessions = survey_data.get('sessions', [])
    
    for session in sessions:
        session_id = session.get('id')
        messages = session.get('messages', [])
        
        # Process message pairs (assistant question -> user answer)
        for i in range(len(messages) - 1):
            if messages[i].get('role') == 'assistant' and messages[i+1].get('role') == 'user':
                question_text = messages[i].get('content', '').strip()
                answer_text = messages[i+1].get('content', '').strip()
                
                # Skip empty answers
                if not answer_text or len(answer_text) < 3:
                    continue
                
                # Try to match to a question ID
                matched_q_id = None
                for q_id, q_info in question_map.items():
                    if q_info['text'] and q_info['text'][:50] in question_text:
                        matched_q_id = q_id
                        break
                
                # If no match, create a generic question entry
                if not matched_q_id:
                    matched_q_id = f"q_{len(qa_pairs)}"
                    if matched_q_id not in question_map:
                        question_map[matched_q_id] = {
                            'id': matched_q_id,
                            'text': question_text,
                            'topic': 'その他'
                        }
                
                qa_pairs[matched_q_id].append({
                    'question': question_map[matched_q_id]['text'],
                    'topic': question_map[matched_q_id].get('topic', ''),
                    'answer': answer_text,
                    'session_id': session_id
                })
    
    return dict(qa_pairs)


def create_batch_summary_prompt(
    question: str,
    answers: List[str],
    topic: str = ""
) -> str:
    """Create prompt for batch summarization."""
    topic_text = f"（トピック: {topic}）" if topic else ""
    
    prompt = f"""以下のアンケート質問に対する{len(answers)}件の回答を分析し、要約してください。

質問{topic_text}:
{question}

回答データ:
"""
    
    for i, answer in enumerate(answers, 1):
        prompt += f"\n【回答{i}】\n{answer}\n"
    
    prompt += """

以下の観点で要約してください:
1. 主要な意見・傾向（多く見られた回答パターン）
2. 特徴的な意見（少数派だが重要な視点）
3. 賛成・反対・中立などの分布（該当する場合）
4. その他注目すべき点

要約は簡潔かつ具体的に、重要なキーワードを含めてください。
"""
    
    return prompt


def create_final_summary_prompt(
    question: str,
    batch_summaries: List[str],
    total_responses: int,
    topic: str = ""
) -> str:
    """Create prompt for final summary integration."""
    topic_text = f"（トピック: {topic}）" if topic else ""
    
    prompt = f"""以下は同じアンケート質問に対する複数のバッチ要約です。
これらを統合して、全体の傾向と主要な意見をまとめてください。

質問{topic_text}:
{question}

総回答数: {total_responses}件

バッチ要約:
"""
    
    for i, summary in enumerate(batch_summaries, 1):
        prompt += f"\n【バッチ{i}】\n{summary}\n"
    
    prompt += """

統合要約を作成する際の要点:
1. 全体的な傾向と主要な意見
2. 意見の分布や多様性
3. 特に重要または特徴的な意見
4. 数値的な傾向（あれば）

統合要約:
"""
    
    return prompt


def summarize_question_responses(
    question_id: str,
    question_text: str,
    qa_data: List[Dict[str, str]],
    provider: LLMProvider,
    batch_size: int = DEFAULT_BATCH_SIZE,
    use_smart_splitting: bool = True
) -> Dict[str, Any]:
    """
    Summarize all responses for a single question with smart splitting.
    
    Args:
        question_id: Question identifier
        question_text: The question text
        qa_data: List of QA pairs for this question
        provider: LLM provider instance
        batch_size: Number of responses per batch
        use_smart_splitting: Use smart splitter for optimal chunk sizing
    
    Returns:
        Summary data dictionary
    """
    if not qa_data:
        return {
            'question_id': question_id,
            'question': question_text,
            'topic': '',
            'num_responses': 0,
            'summary': '回答なし'
        }
    
    topic = qa_data[0].get('topic', '')
    answers = [qa['answer'] for qa in qa_data]
    
    # Use smart splitting if enabled
    if use_smart_splitting and len(qa_data) > batch_size:
        estimated_tokens = estimate_chunk_tokens(qa_data)
        optimal_batch_size = calculate_optimal_chunk_size(len(qa_data), estimated_tokens)
        print(f"      Smart splitting: {len(qa_data)} responses → {optimal_batch_size} per batch")
        batch_size = optimal_batch_size
    
    # If responses fit in one batch, summarize directly
    if len(answers) <= batch_size:
        prompt = create_batch_summary_prompt(question_text, answers, topic)
        summary = provider.generate(
            prompt,
            max_tokens=SUMMARY_MAX_TOKENS,
            temperature=SUMMARY_TEMPERATURE
        )
        
        return {
            'question_id': question_id,
            'question': question_text,
            'topic': topic,
            'num_responses': len(answers),
            'summary': summary
        }
    
    # Process in batches (Level 1: Small batches)
    batch_summaries = []
    for i in range(0, len(answers), batch_size):
        batch = answers[i:i+batch_size]
        prompt = create_batch_summary_prompt(question_text, batch, topic)
        
        batch_summary = provider.generate(
            prompt,
            max_tokens=SUMMARY_MAX_TOKENS,
            temperature=SUMMARY_TEMPERATURE
        )
        batch_summaries.append(batch_summary)
    
    # Level 2: If too many batch summaries, create intermediate summaries
    if len(batch_summaries) > 10:
        print(f"      Hierarchical summarization: {len(batch_summaries)} batches → intermediate level")
        intermediate_summaries = []
        intermediate_batch_size = 5
        
        for i in range(0, len(batch_summaries), intermediate_batch_size):
            intermediate_batch = batch_summaries[i:i+intermediate_batch_size]
            intermediate_prompt = f"""以下は同じ質問に対する{len(intermediate_batch)}個のバッチ要約です。
これらを統合して中間要約を作成してください。

質問: {question_text}

バッチ要約:
"""
            for j, summary in enumerate(intermediate_batch, 1):
                intermediate_prompt += f"\n【バッチ{i+j}】\n{summary}\n"
            
            intermediate_prompt += "\n統合された要約:"
            
            intermediate_summary = provider.generate(
                intermediate_prompt,
                max_tokens=SUMMARY_MAX_TOKENS,
                temperature=SUMMARY_TEMPERATURE
            )
            intermediate_summaries.append(intermediate_summary)
        
        # Use intermediate summaries for final integration
        batch_summaries = intermediate_summaries
    
    # Level 3: Final integration
    if len(batch_summaries) > 1:
        final_prompt = create_final_summary_prompt(
            question_text,
            batch_summaries,
            len(answers),
            topic
        )
        
        final_summary = provider.generate(
            final_prompt,
            max_tokens=SUMMARY_MAX_TOKENS,
            temperature=SUMMARY_TEMPERATURE
        )
    else:
        final_summary = batch_summaries[0]
    
    return {
        'question_id': question_id,
        'question': question_text,
        'topic': topic,
        'num_responses': len(answers),
        'batch_summaries': batch_summaries,
        'summary': final_summary
    }


def summarize_survey(
    survey_file: Path,
    provider: LLMProvider,
    batch_size: int = DEFAULT_BATCH_SIZE
) -> Dict[str, Any]:
    """
    Summarize all questions in a survey.
    
    Args:
        survey_file: Path to survey chunk JSON
        provider: LLM provider instance
        batch_size: Batch size for processing
    
    Returns:
        Complete survey summary
    """
    print(f"\n📊 Processing: {survey_file.name}")
    
    # Load survey data
    survey_data = load_survey_chunk(survey_file)
    config = survey_data.get('config', {})
    
    # Extract QA pairs
    qa_pairs = extract_qa_pairs(survey_data)
    
    print(f"   Found {len(qa_pairs)} questions with responses")
    
    # Summarize each question
    question_summaries = []
    
    for question_id, qa_list in tqdm(qa_pairs.items(), desc="   Summarizing"):
        if qa_list:
            question_text = qa_list[0]['question']
            summary = summarize_question_responses(
                question_id,
                question_text,
                qa_list,
                provider,
                batch_size
            )
            question_summaries.append(summary)
    
    # Create survey summary
    survey_summary = {
        'slug': config.get('slug'),
        'title': config.get('title'),
        'description': config.get('description'),
        'num_sessions': survey_data.get('stats', {}).get('num_sessions', 0),
        'num_questions': len(question_summaries),
        'provider': provider.get_name(),
        'model': provider.model_name,
        'question_summaries': question_summaries
    }
    
    return survey_summary


def save_summary(
    summary: Dict[str, Any],
    output_dir: Path,
    provider_name: str
):
    """Save summary to JSON file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    slug = summary['slug']
    output_file = output_dir / f"{slug}_summary.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"   ✅ Summary saved: {output_file.name}")


def process_all_surveys(
    provider_name: str,
    batch_size: int = DEFAULT_BATCH_SIZE,
    survey_filter: Optional[str] = None,
    model_name: Optional[str] = None
):
    """
    Process all survey chunks with specified LLM provider.
    
    Args:
        provider_name: Name of LLM provider ("claude", "gemini", or "ollama")
        batch_size: Batch size for processing
        survey_filter: Optional slug filter (process only this survey)
        model_name: Optional model name (used for Ollama)
    """
    print("\n" + "="*70)
    print(f"SURVEY SUMMARIZATION - {provider_name.upper()}")
    print("="*70)
    
    # Initialize provider
    try:
        provider = get_provider(provider_name, model_name)
        print(f"✅ {provider_name.upper()} provider initialized")
        print(f"   Model: {provider.model_name}")
    except Exception as e:
        print(f"❌ Failed to initialize {provider_name} provider: {e}")
        return
    
    # Get survey files
    survey_files = sorted(SURVEY_CHUNKS_DIR.glob("survey_*.json"))
    
    if survey_filter:
        survey_files = [f for f in survey_files if survey_filter in f.name]
    
    if not survey_files:
        print(f"❌ No survey files found in {SURVEY_CHUNKS_DIR}")
        return
    
    print(f"\n📁 Found {len(survey_files)} survey(s) to process")
    
    # Process each survey
    output_dir = get_output_dir(provider_name)
    all_summaries = []
    
    for survey_file in survey_files:
        try:
            summary = summarize_survey(survey_file, provider, batch_size)
            save_summary(summary, output_dir, provider_name)
            all_summaries.append(summary)
        except Exception as e:
            print(f"   ❌ Error processing {survey_file.name}: {e}")
            continue
    
    # Print final statistics
    print("\n" + "="*70)
    print("SUMMARIZATION COMPLETE")
    print("="*70)
    print(f"Provider: {provider_name.upper()}")
    print(f"Surveys processed: {len(all_summaries)}")
    print(f"Total API requests: {provider.request_count}")
    print(f"Total tokens used: {provider.total_tokens:,}")
    print(f"Output directory: {output_dir}")
    print("="*70 + "\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Summarize survey responses using LLMs"
    )
    parser.add_argument(
        '--llm',
        choices=['claude', 'gemini', 'ollama', 'both', 'all'],
        default='both',
        help='LLM provider to use'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f'Batch size for processing (default: {DEFAULT_BATCH_SIZE})'
    )
    parser.add_argument(
        '--survey',
        type=str,
        help='Process only surveys matching this slug'
    )
    parser.add_argument(
        '--model',
        type=str,
        help='Model name (used for Ollama, default: gpt-oss20b)'
    )
    
    args = parser.parse_args()
    
    # Process with selected provider(s)
    if args.llm in ['claude', 'both', 'all']:
        process_all_surveys('claude', args.batch_size, args.survey)
    
    if args.llm in ['gemini', 'both', 'all']:
        process_all_surveys('gemini', args.batch_size, args.survey)
    
    if args.llm in ['ollama', 'all']:
        process_all_surveys('ollama', args.batch_size, args.survey, args.model)
    
    print("✨ All summarization tasks complete!")


if __name__ == "__main__":
    main()

