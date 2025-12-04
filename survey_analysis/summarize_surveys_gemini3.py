#!/usr/bin/env python3
"""
Summarize survey responses using Google Gemini 3 Pro Preview.

This script processes survey chunks and generates summaries for each
question using Gemini 3 Pro Preview via Google API.

Requirements:
- Python 3.11+ (conda activate mirai_db_analysis_py3.11)
- Google API Key in .env file

Usage:
    python summarize_surveys_gemini3.py [--batch-size 10] [--survey SLUG] [--model MODEL_NAME]
"""

import json
import os
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
from collections import defaultdict
from tqdm import tqdm
from dotenv import load_dotenv
import time

import google.generativeai as genai


# ============================================================================
# Configuration
# ============================================================================

# Load environment variables from .env file
load_dotenv()

# Base directories
BASE_DIR = Path(__file__).parent
PROJECT_ROOT = BASE_DIR.parent

# Input/Output directories
SURVEY_CHUNKS_DIR = BASE_DIR / "survey_chunks"
SURVEY_SUMMARIES_DIR = BASE_DIR / "survey_summaries"
GEMINI3_OUTPUT_DIR = SURVEY_SUMMARIES_DIR / "gemini3" / "summaries"

# Gemini configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Available Gemini 3 Pro Preview models
GEMINI3_MODELS = {
    "exp-1206": "gemini-exp-1206",  # Gemini 3 Pro Preview (Dec 2024)
    "2.0-flash-exp": "gemini-2.0-flash-exp",  # Gemini 2.0 Flash Experimental
    "2.0-flash-thinking-exp": "gemini-2.0-flash-thinking-exp-1219",  # With thinking mode
}

DEFAULT_GEMINI3_MODEL = "gemini-exp-1206"

# API request settings
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds
REQUEST_TIMEOUT = 120  # seconds

# Processing parameters
DEFAULT_BATCH_SIZE = 10
SUMMARY_MAX_TOKENS = 4096
SUMMARY_TEMPERATURE = 0.7


# ============================================================================
# Gemini 3 Provider
# ============================================================================

class Gemini3Provider:
    """Google Gemini 3 Pro Preview provider."""
    
    def __init__(self, model_name: str = DEFAULT_GEMINI3_MODEL):
        """Initialize Gemini 3 provider."""
        self.model_name = model_name
        self.request_count = 0
        self.total_tokens = 0
        
        if not GOOGLE_API_KEY:
            raise ValueError(
                "GOOGLE_API_KEY not found in environment variables.\n"
                "Please create a .env file with: GOOGLE_API_KEY=your_api_key_here"
            )
        
        # Configure Gemini API
        genai.configure(api_key=GOOGLE_API_KEY)
        
        # Initialize model
        self.model = genai.GenerativeModel(self.model_name)
        
        print(f"✅ Gemini 3 Pro Preview initialized: {self.model_name}")
    
    def generate(
        self,
        prompt: str,
        max_tokens: int = SUMMARY_MAX_TOKENS,
        temperature: float = SUMMARY_TEMPERATURE,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Generate text using Gemini 3.
        
        Args:
            prompt: User prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            system_prompt: Optional system prompt
        
        Returns:
            Generated text response
        """
        # Combine system prompt and user prompt for Gemini
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        for attempt in range(MAX_RETRIES):
            try:
                generation_config = genai.types.GenerationConfig(
                    max_output_tokens=max_tokens,
                    temperature=temperature,
                )
                
                response = self.model.generate_content(
                    full_prompt,
                    generation_config=generation_config
                )
                
                self.request_count += 1
                
                # Track token usage
                if hasattr(response, 'usage_metadata'):
                    self.total_tokens += (
                        response.usage_metadata.prompt_token_count +
                        response.usage_metadata.candidates_token_count
                    )
                
                return response.text
            
            except Exception as e:
                error_str = str(e).lower()
                
                # Handle rate limiting
                if "429" in str(e) or "quota" in error_str or "rate" in error_str:
                    if attempt < MAX_RETRIES - 1:
                        wait_time = RETRY_DELAY * (attempt + 1)  # Exponential backoff
                        print(f"⚠️  Rate limit hit, waiting {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        raise
                
                # Handle other errors
                elif attempt < MAX_RETRIES - 1:
                    print(f"⚠️  Error: {e}, retrying...")
                    time.sleep(RETRY_DELAY)
                else:
                    raise
    
    def get_name(self) -> str:
        """Get provider name."""
        return "gemini3"
    
    def get_stats(self) -> Dict[str, Any]:
        """Get usage statistics."""
        return {
            'provider': self.get_name(),
            'model': self.model_name,
            'request_count': self.request_count,
            'total_tokens': self.total_tokens
        }


# ============================================================================
# Survey Processing Functions
# ============================================================================

def load_survey_chunk(file_path: Path) -> dict:
    """Load a survey chunk JSON file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_qa_pairs(survey_data: dict) -> Dict[str, List[Dict[str, str]]]:
    """
    Extract question-answer pairs from survey data.
    
    Returns:
        Dict mapping question_id to list of {question, answer, topic, session_id}
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
    provider: Gemini3Provider,
    batch_size: int = DEFAULT_BATCH_SIZE
) -> Dict[str, Any]:
    """
    Summarize all responses for a single question.
    
    Args:
        question_id: Question identifier
        question_text: The question text
        qa_data: List of QA pairs for this question
        provider: Gemini3 provider instance
        batch_size: Number of responses per batch
    
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
    
    # If responses fit in one batch, summarize directly
    if len(answers) <= batch_size:
        prompt = create_batch_summary_prompt(question_text, answers, topic)
        summary = provider.generate(prompt)
        
        return {
            'question_id': question_id,
            'question': question_text,
            'topic': topic,
            'num_responses': len(answers),
            'summary': summary
        }
    
    # Process in batches
    print(f"      Processing {len(answers)} responses in batches of {batch_size}")
    batch_summaries = []
    
    for i in range(0, len(answers), batch_size):
        batch = answers[i:i+batch_size]
        prompt = create_batch_summary_prompt(question_text, batch, topic)
        batch_summary = provider.generate(prompt)
        batch_summaries.append(batch_summary)
    
    # Hierarchical summarization if too many batches
    if len(batch_summaries) > 10:
        print(f"      Hierarchical summarization: {len(batch_summaries)} batches")
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
            
            intermediate_summary = provider.generate(intermediate_prompt)
            intermediate_summaries.append(intermediate_summary)
        
        batch_summaries = intermediate_summaries
    
    # Final integration
    if len(batch_summaries) > 1:
        final_prompt = create_final_summary_prompt(
            question_text,
            batch_summaries,
            len(answers),
            topic
        )
        final_summary = provider.generate(final_prompt)
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
    provider: Gemini3Provider,
    batch_size: int = DEFAULT_BATCH_SIZE
) -> Dict[str, Any]:
    """
    Summarize all questions in a survey.
    
    Args:
        survey_file: Path to survey chunk JSON
        provider: Gemini3 provider instance
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


def save_summary(summary: Dict[str, Any], output_dir: Path):
    """Save summary to JSON file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    slug = summary['slug']
    output_file = output_dir / f"{slug}_summary.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"   ✅ Summary saved: {output_file.name}")


def process_all_surveys(
    model_name: str = DEFAULT_GEMINI3_MODEL,
    batch_size: int = DEFAULT_BATCH_SIZE,
    survey_filter: Optional[str] = None
):
    """
    Process all survey chunks with Gemini 3 Pro Preview.
    
    Args:
        model_name: Gemini 3 model name
        batch_size: Batch size for processing
        survey_filter: Optional slug filter (process only this survey)
    """
    print("\n" + "="*70)
    print("SURVEY SUMMARIZATION - GEMINI 3 PRO PREVIEW")
    print("="*70)
    
    # Initialize provider
    try:
        provider = Gemini3Provider(model_name)
        print(f"   Model: {provider.model_name}")
    except Exception as e:
        print(f"❌ Failed to initialize Gemini 3 provider: {e}")
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
    all_summaries = []
    
    for survey_file in survey_files:
        try:
            summary = summarize_survey(survey_file, provider, batch_size)
            save_summary(summary, GEMINI3_OUTPUT_DIR)
            all_summaries.append(summary)
        except Exception as e:
            print(f"   ❌ Error processing {survey_file.name}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # Print final statistics
    print("\n" + "="*70)
    print("SUMMARIZATION COMPLETE")
    print("="*70)
    print(f"Provider: GEMINI 3 PRO PREVIEW")
    print(f"Model: {provider.model_name}")
    print(f"Surveys processed: {len(all_summaries)}")
    print(f"Total API requests: {provider.request_count}")
    print(f"Total tokens used: {provider.total_tokens:,}")
    print(f"Output directory: {GEMINI3_OUTPUT_DIR}")
    print("="*70 + "\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Summarize survey responses using Gemini 3 Pro Preview",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Available Models:
  exp-1206              : {GEMINI3_MODELS['exp-1206']} (default)
  2.0-flash-exp         : {GEMINI3_MODELS['2.0-flash-exp']}
  2.0-flash-thinking-exp: {GEMINI3_MODELS['2.0-flash-thinking-exp']}

Examples:
  # Use default model
  python summarize_surveys_gemini3.py
  
  # Use specific model
  python summarize_surveys_gemini3.py --model 2.0-flash-exp
  
  # Process specific survey
  python summarize_surveys_gemini3.py --survey plan2026
  
  # Custom batch size
  python summarize_surveys_gemini3.py --batch-size 20
        """
    )
    
    parser.add_argument(
        '--model',
        choices=list(GEMINI3_MODELS.keys()),
        default='exp-1206',
        help='Gemini 3 model to use (default: exp-1206)'
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
    
    args = parser.parse_args()
    
    # Get full model name
    model_name = GEMINI3_MODELS[args.model]
    
    # Check for API key
    if not GOOGLE_API_KEY:
        print("❌ Error: GOOGLE_API_KEY not found in environment variables")
        print("\nPlease create a .env file in the survey_analysis directory with:")
        print("GOOGLE_API_KEY=your_api_key_here")
        print("\nOr set the environment variable:")
        print("export GOOGLE_API_KEY=your_api_key_here")
        return
    
    # Process surveys
    process_all_surveys(model_name, args.batch_size, args.survey)
    
    print("✨ All summarization tasks complete!")


if __name__ == "__main__":
    main()












