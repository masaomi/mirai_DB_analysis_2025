#!/usr/bin/env python3
"""
Test script to process a single survey file.
"""
from pathlib import Path
from summarize_surveys import summarize_survey
from llm_providers import get_provider
from config import get_output_dir

# Configuration
SURVEY_FILE = Path("survey_chunks/survey_marumie-shikin.json")
PROVIDER_NAME = "ollama"
MODEL_NAME = "gpt-oss:20b"
BATCH_SIZE = 10

def main():
    print(f"\n{'='*70}")
    print(f"SINGLE SURVEY SUMMARIZATION - {PROVIDER_NAME.upper()}")
    print(f"{'='*70}\n")
    
    # Initialize provider
    print(f"Initializing {PROVIDER_NAME} provider...")
    provider = get_provider(PROVIDER_NAME, MODEL_NAME)
    print(f"✅ Provider initialized: {provider.model_name}\n")
    
    # Process survey
    print(f"Processing: {SURVEY_FILE.name}")
    summary = summarize_survey(SURVEY_FILE, provider, BATCH_SIZE)
    
    # Save summary
    output_dir = get_output_dir(PROVIDER_NAME)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    import json
    output_file = output_dir / f"{summary['slug']}_summary.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Summary saved: {output_file.name}")
    print(f"\nStats:")
    print(f"  - Questions processed: {summary['num_questions']}")
    print(f"  - API requests: {provider.request_count}")
    print(f"  - Tokens used: {provider.total_tokens:,}")
    print(f"\n{'='*70}\n")

if __name__ == "__main__":
    main()











