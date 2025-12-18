#!/usr/bin/env python3
"""
Summarize survey responses using Amazon Bedrock (Claude Sonnet 4.5).

This script processes survey chunks and generates summaries for each
question using Claude Sonnet 4.5 via Amazon Bedrock.

Requirements:
- Python 3.11+ (conda activate mirai_db_analysis_py3.11)
- AWS Credentials (Bearer Token or Access Keys)
- Bedrock model access enabled

Usage:
    python summarize_surveys_bedrock.py [--batch-size 10] [--survey SLUG] [--model MODEL_ID]
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
import boto3
from botocore.config import Config
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest


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
BEDROCK_OUTPUT_DIR = SURVEY_SUMMARIES_DIR / "bedrock" / "summaries"

# AWS Bedrock configuration
AWS_REGION = os.getenv("AWS_REGION", "eu-central-1")
AWS_BEARER_TOKEN = os.getenv("AWS_BEARER_TOKEN_BEDROCK")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

# Available Bedrock Claude models
BEDROCK_MODELS = {
    # Claude Sonnet 4.5 Inference Profiles (requires Bearer token)
    "sonnet-4.5-eu": "eu.anthropic.claude-sonnet-4-5-20250929-v1:0",
    "sonnet-4.5-us": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    
    # Claude 3.5 Sonnet (Direct model access)
    "sonnet-3.5": "anthropic.claude-3-5-sonnet-20241022-v2:0",
    
    # Other Claude models
    "sonnet-3": "anthropic.claude-3-sonnet-20240229-v1:0",
    "haiku-3": "anthropic.claude-3-haiku-20240307-v1:0",
}

# Default model
DEFAULT_BEDROCK_MODEL = "sonnet-4.5-eu"

# API request settings
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds
REQUEST_TIMEOUT = 120  # seconds

# Processing parameters
DEFAULT_BATCH_SIZE = 10
SUMMARY_MAX_TOKENS = 4096
SUMMARY_TEMPERATURE = 0.7


# ============================================================================
# Bedrock Provider
# ============================================================================

class BedrockProvider:
    """Amazon Bedrock Claude provider."""
    
    def __init__(self, model_id: str = None, region: str = AWS_REGION):
        """Initialize Bedrock provider."""
        self.region = region
        self.model_id = model_id or BEDROCK_MODELS[DEFAULT_BEDROCK_MODEL]
        self.request_count = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        
        # Validate credentials
        if not region:
            raise ValueError(
                "AWS_REGION not found in environment variables.\n"
                "Please set AWS_REGION in your .env file"
            )
        
        # Initialize Bedrock client based on authentication method
        self.use_bearer_token = bool(AWS_BEARER_TOKEN)
        
        if self.use_bearer_token:
            print(f"✅ Using Bearer Token authentication for Bedrock")
            # For Bearer token, we still need boto3 client but will inject token manually
            self.client = boto3.client(
                'bedrock-runtime',
                region_name=self.region,
                config=Config(
                    retries={'max_attempts': MAX_RETRIES, 'mode': 'adaptive'}
                )
            )
            self.bearer_token = AWS_BEARER_TOKEN
        elif AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
            print(f"✅ Using Access Key authentication for Bedrock")
            self.client = boto3.client(
                'bedrock-runtime',
                region_name=self.region,
                aws_access_key_id=AWS_ACCESS_KEY_ID,
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                config=Config(
                    retries={'max_attempts': MAX_RETRIES, 'mode': 'adaptive'}
                )
            )
            self.bearer_token = None
        else:
            raise ValueError(
                "AWS credentials not found.\n"
                "Please provide either:\n"
                "  - AWS_BEARER_TOKEN_BEDROCK (for Inference Profiles)\n"
                "  or\n"
                "  - AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY\n"
                "in your .env file"
            )
        
        print(f"✅ Bedrock initialized: {self.model_id} in {self.region}")
    
    def generate(
        self,
        prompt: str,
        max_tokens: int = SUMMARY_MAX_TOKENS,
        temperature: float = SUMMARY_TEMPERATURE,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Generate text using Bedrock Claude.
        
        Args:
            prompt: User prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            system_prompt: Optional system prompt
        
        Returns:
            Generated text response
        """
        for attempt in range(MAX_RETRIES):
            try:
                # Build messages in Claude format
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
                
                # Prepare request body
                body = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "messages": messages
                }
                
                # Add system prompt if provided
                if system_prompt:
                    body["system"] = system_prompt
                
                # Make request to Bedrock
                if self.use_bearer_token:
                    # Use Bearer token authentication
                    response = self._invoke_with_bearer_token(body)
                else:
                    # Use standard AWS authentication
                    response = self.client.invoke_model(
                        modelId=self.model_id,
                        contentType='application/json',
                        accept='application/json',
                        body=json.dumps(body)
                    )
                    response_body = json.loads(response['body'].read())
                
                # Extract response
                if self.use_bearer_token:
                    response_body = response
                
                self.request_count += 1
                
                # Track token usage
                if 'usage' in response_body:
                    self.total_input_tokens += response_body['usage'].get('input_tokens', 0)
                    self.total_output_tokens += response_body['usage'].get('output_tokens', 0)
                
                # Extract content
                content = ''
                if 'content' in response_body and isinstance(response_body['content'], list):
                    for item in response_body['content']:
                        if item.get('type') == 'text':
                            content += item.get('text', '')
                
                return content.strip()
            
            except Exception as e:
                error_str = str(e).lower()
                
                # Handle throttling
                if 'throttling' in error_str or 'rate' in error_str or '429' in str(e):
                    if attempt < MAX_RETRIES - 1:
                        wait_time = RETRY_DELAY * (attempt + 1)
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
        
        raise Exception("Failed to generate response after all retries")
    
    def _invoke_with_bearer_token(self, body: dict) -> dict:
        """
        Invoke Bedrock model with Bearer token authentication.
        
        This method manually constructs the HTTP request with Bearer token.
        """
        import requests
        
        endpoint = f"https://bedrock-runtime.{self.region}.amazonaws.com/model/{self.model_id}/invoke"
        
        headers = {
            'Authorization': f'Bearer {self.bearer_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        response = requests.post(
            endpoint,
            headers=headers,
            json=body,
            timeout=REQUEST_TIMEOUT
        )
        
        response.raise_for_status()
        return response.json()
    
    def get_name(self) -> str:
        """Get provider name."""
        return "bedrock"
    
    def get_stats(self) -> Dict[str, Any]:
        """Get usage statistics."""
        return {
            'provider': self.get_name(),
            'model': self.model_id,
            'region': self.region,
            'request_count': self.request_count,
            'total_input_tokens': self.total_input_tokens,
            'total_output_tokens': self.total_output_tokens,
            'total_tokens': self.total_input_tokens + self.total_output_tokens
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
    provider: BedrockProvider,
    batch_size: int = DEFAULT_BATCH_SIZE
) -> Dict[str, Any]:
    """
    Summarize all responses for a single question.
    
    Args:
        question_id: Question identifier
        question_text: The question text
        qa_data: List of QA pairs for this question
        provider: Bedrock provider instance
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
    provider: BedrockProvider,
    batch_size: int = DEFAULT_BATCH_SIZE
) -> Dict[str, Any]:
    """
    Summarize all questions in a survey.
    
    Args:
        survey_file: Path to survey chunk JSON
        provider: Bedrock provider instance
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
        'model': provider.model_id,
        'region': provider.region,
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
    model_key: str = DEFAULT_BEDROCK_MODEL,
    batch_size: int = DEFAULT_BATCH_SIZE,
    survey_filter: Optional[str] = None
):
    """
    Process all survey chunks with Amazon Bedrock.
    
    Args:
        model_key: Bedrock model key
        batch_size: Batch size for processing
        survey_filter: Optional slug filter (process only this survey)
    """
    print("\n" + "="*70)
    print("SURVEY SUMMARIZATION - AMAZON BEDROCK")
    print("="*70)
    
    # Get model ID
    model_id = BEDROCK_MODELS.get(model_key)
    if not model_id:
        print(f"❌ Unknown model key: {model_key}")
        print(f"Available models: {', '.join(BEDROCK_MODELS.keys())}")
        return
    
    # Initialize provider
    try:
        provider = BedrockProvider(model_id)
        print(f"   Model: {provider.model_id}")
        print(f"   Region: {provider.region}")
    except Exception as e:
        print(f"❌ Failed to initialize Bedrock provider: {e}")
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
            save_summary(summary, BEDROCK_OUTPUT_DIR)
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
    print(f"Provider: AMAZON BEDROCK")
    print(f"Model: {provider.model_id}")
    print(f"Region: {provider.region}")
    print(f"Surveys processed: {len(all_summaries)}")
    print(f"Total API requests: {provider.request_count}")
    print(f"Total input tokens: {provider.total_input_tokens:,}")
    print(f"Total output tokens: {provider.total_output_tokens:,}")
    print(f"Total tokens: {provider.total_input_tokens + provider.total_output_tokens:,}")
    print(f"Output directory: {BEDROCK_OUTPUT_DIR}")
    print("="*70 + "\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Summarize survey responses using Amazon Bedrock (Claude Sonnet 4.5)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Available Models:
  sonnet-4.5-eu  : {BEDROCK_MODELS['sonnet-4.5-eu']} (default, requires Bearer token)
  sonnet-4.5-us  : {BEDROCK_MODELS['sonnet-4.5-us']} (requires Bearer token)
  sonnet-3.5     : {BEDROCK_MODELS['sonnet-3.5']} (Access Key auth)
  sonnet-3       : {BEDROCK_MODELS['sonnet-3']}
  haiku-3        : {BEDROCK_MODELS['haiku-3']}

Examples:
  # Use default model (Sonnet 4.5 EU)
  python summarize_surveys_bedrock.py
  
  # Use Sonnet 3.5 with Access Key auth
  python summarize_surveys_bedrock.py --model sonnet-3.5
  
  # Process specific survey
  python summarize_surveys_bedrock.py --survey marumie-shikin
  
  # Custom batch size
  python summarize_surveys_bedrock.py --batch-size 20
        """
    )
    
    parser.add_argument(
        '--model',
        choices=list(BEDROCK_MODELS.keys()),
        default=DEFAULT_BEDROCK_MODEL,
        help=f'Bedrock model to use (default: {DEFAULT_BEDROCK_MODEL})'
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
    
    # Check for AWS credentials
    if not (AWS_BEARER_TOKEN or (AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY)):
        print("❌ Error: AWS credentials not found")
        print("\nPlease provide either:")
        print("  - AWS_BEARER_TOKEN_BEDROCK (for Sonnet 4.5 Inference Profiles)")
        print("  or")
        print("  - AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
        print("\nCreate a .env file with your credentials:")
        print("  cp env_bedrock_sample.txt .env")
        print("  nano .env")
        return
    
    # Process surveys
    process_all_surveys(args.model, args.batch_size, args.survey)
    
    print("✨ All summarization tasks complete!")


if __name__ == "__main__":
    main()



















