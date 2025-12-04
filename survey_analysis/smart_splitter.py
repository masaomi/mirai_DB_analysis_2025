#!/usr/bin/env python3
"""
Smart file splitting module for large survey data.

This module analyzes survey files and automatically splits them into
manageable chunks based on size, response count, and estimated token count.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass


# Thresholds for splitting
FILE_SIZE_THRESHOLD_MB = 5  # Split if file is larger than 5MB
RESPONSE_COUNT_THRESHOLD = 100  # Split if more than 100 responses per question
ESTIMATED_TOKEN_THRESHOLD = 50000  # Split if estimated tokens exceed 50K


@dataclass
class SplitMetadata:
    """Metadata for a split chunk."""
    chunk_id: int
    total_chunks: int
    question_id: str
    start_index: int
    end_index: int
    response_count: int


def estimate_tokens(text: str) -> int:
    """
    Estimate token count for Japanese text.
    
    Rough estimation: 1 token ≈ 2 characters for Japanese
    """
    return len(text) // 2


def estimate_chunk_tokens(qa_data: List[Dict[str, str]]) -> int:
    """Estimate total tokens for a list of Q&A pairs."""
    total = 0
    for qa in qa_data:
        question = qa.get('question', '')
        answer = qa.get('answer', '')
        total += estimate_tokens(question) + estimate_tokens(answer)
    return total


def should_split_question(
    qa_data: List[Dict[str, str]],
    file_size_mb: float = 0
) -> bool:
    """
    Determine if a question's responses should be split.
    
    Args:
        qa_data: List of Q&A pairs for a question
        file_size_mb: Size of the source file in MB
    
    Returns:
        True if splitting is recommended
    """
    # Check response count
    if len(qa_data) > RESPONSE_COUNT_THRESHOLD:
        return True
    
    # Check estimated tokens
    estimated_tokens = estimate_chunk_tokens(qa_data)
    if estimated_tokens > ESTIMATED_TOKEN_THRESHOLD:
        return True
    
    # Check file size
    if file_size_mb > FILE_SIZE_THRESHOLD_MB:
        return True
    
    return False


def calculate_optimal_chunk_size(
    total_responses: int,
    estimated_tokens: int
) -> int:
    """
    Calculate optimal chunk size based on total responses and tokens.
    
    Returns:
        Recommended chunk size (number of responses per chunk)
    """
    # Aim for ~10K tokens per chunk
    target_tokens = 10000
    
    if estimated_tokens == 0:
        return min(20, total_responses)  # Default to 20 if can't estimate
    
    avg_tokens_per_response = estimated_tokens / total_responses
    optimal_size = int(target_tokens / avg_tokens_per_response)
    
    # Ensure reasonable bounds (10-50 responses per chunk)
    return max(10, min(50, optimal_size))


def split_qa_data(
    question_id: str,
    qa_data: List[Dict[str, str]],
    chunk_size: int = None
) -> List[Tuple[List[Dict[str, str]], SplitMetadata]]:
    """
    Split Q&A data into manageable chunks.
    
    Args:
        question_id: Question identifier
        qa_data: List of Q&A pairs
        chunk_size: Optional chunk size (auto-calculated if not provided)
    
    Returns:
        List of (chunk_data, metadata) tuples
    """
    if not qa_data:
        return []
    
    # Calculate chunk size if not provided
    if chunk_size is None:
        estimated_tokens = estimate_chunk_tokens(qa_data)
        chunk_size = calculate_optimal_chunk_size(len(qa_data), estimated_tokens)
    
    # Split into chunks
    chunks = []
    total_chunks = (len(qa_data) + chunk_size - 1) // chunk_size
    
    for i in range(0, len(qa_data), chunk_size):
        chunk_data = qa_data[i:i+chunk_size]
        chunk_id = i // chunk_size
        
        metadata = SplitMetadata(
            chunk_id=chunk_id,
            total_chunks=total_chunks,
            question_id=question_id,
            start_index=i,
            end_index=min(i + chunk_size, len(qa_data)),
            response_count=len(chunk_data)
        )
        
        chunks.append((chunk_data, metadata))
    
    return chunks


def analyze_survey_file(survey_file: Path) -> Dict[str, Any]:
    """
    Analyze a survey file and provide splitting recommendations.
    
    Args:
        survey_file: Path to survey JSON file
    
    Returns:
        Analysis results with splitting recommendations
    """
    # Load survey data
    with open(survey_file, 'r', encoding='utf-8') as f:
        survey_data = json.load(f)
    
    # Get file size
    file_size_mb = survey_file.stat().st_size / (1024 * 1024)
    
    # Extract basic info
    config = survey_data.get('config', {})
    sessions = survey_data.get('sessions', [])
    
    # Analyze questions
    questions_analysis = []
    
    # Extract Q&A pairs (simplified version)
    from extract_surveys import compile_survey_data
    from summarize_surveys import extract_qa_pairs
    
    qa_pairs = extract_qa_pairs(survey_data)
    
    for question_id, qa_list in qa_pairs.items():
        if not qa_list:
            continue
        
        estimated_tokens = estimate_chunk_tokens(qa_list)
        should_split = should_split_question(qa_list, file_size_mb)
        
        if should_split:
            chunk_size = calculate_optimal_chunk_size(len(qa_list), estimated_tokens)
            num_chunks = (len(qa_list) + chunk_size - 1) // chunk_size
        else:
            chunk_size = len(qa_list)
            num_chunks = 1
        
        questions_analysis.append({
            'question_id': question_id,
            'question_text': qa_list[0]['question'][:100],
            'response_count': len(qa_list),
            'estimated_tokens': estimated_tokens,
            'should_split': should_split,
            'recommended_chunk_size': chunk_size,
            'num_chunks': num_chunks
        })
    
    return {
        'file_path': str(survey_file),
        'file_size_mb': file_size_mb,
        'survey_slug': config.get('slug'),
        'survey_title': config.get('title'),
        'num_sessions': len(sessions),
        'num_questions': len(questions_analysis),
        'total_responses': sum(q['response_count'] for q in questions_analysis),
        'questions': questions_analysis,
        'needs_splitting': any(q['should_split'] for q in questions_analysis)
    }


def print_analysis_report(analysis: Dict[str, Any]):
    """Print a formatted analysis report."""
    print("\n" + "="*70)
    print("SURVEY FILE ANALYSIS")
    print("="*70)
    
    print(f"\nFile: {analysis['file_path']}")
    print(f"Size: {analysis['file_size_mb']:.2f} MB")
    print(f"Survey: {analysis['survey_title']} ({analysis['survey_slug']})")
    print(f"Sessions: {analysis['num_sessions']}")
    print(f"Questions: {analysis['num_questions']}")
    print(f"Total Responses: {analysis['total_responses']:,}")
    
    needs_splitting = analysis['needs_splitting']
    print(f"\nSplitting needed: {'Yes' if needs_splitting else 'No'}")
    
    if needs_splitting:
        print("\nQuestions requiring splitting:")
        for q in analysis['questions']:
            if q['should_split']:
                print(f"\n  • {q['question_id']}: {q['question_text']}...")
                print(f"    - Responses: {q['response_count']:,}")
                print(f"    - Est. tokens: {q['estimated_tokens']:,}")
                print(f"    - Will split into: {q['num_chunks']} chunks")
                print(f"    - Chunk size: ~{q['recommended_chunk_size']} responses")
    
    print("\n" + "="*70 + "\n")


def main():
    """Analyze all survey chunk files."""
    from config import SURVEY_CHUNKS_DIR
    
    survey_files = sorted(SURVEY_CHUNKS_DIR.glob("survey_*.json"))
    
    if not survey_files:
        print(f"No survey files found in {SURVEY_CHUNKS_DIR}")
        return
    
    print(f"\n📊 Analyzing {len(survey_files)} survey file(s)...\n")
    
    all_analyses = []
    for survey_file in survey_files:
        try:
            analysis = analyze_survey_file(survey_file)
            all_analyses.append(analysis)
            print_analysis_report(analysis)
        except Exception as e:
            print(f"❌ Error analyzing {survey_file.name}: {e}\n")
    
    # Summary
    total_needs_splitting = sum(1 for a in all_analyses if a['needs_splitting'])
    
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Total surveys analyzed: {len(all_analyses)}")
    print(f"Surveys needing splitting: {total_needs_splitting}")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()











