#!/usr/bin/env python3
"""
Main pipeline script for survey analysis.

This script orchestrates the entire analysis pipeline:
1. Extract surveys from backup JSON
2. Summarize using LLMs (Claude and/or Gemini)
3. Generate Markdown reports
4. Convert to HTML/PDF formats
"""

import argparse
import sys
import time
from pathlib import Path

# Import pipeline modules
import extract_surveys
import summarize_surveys
import generate_reports
import convert_to_formats
from config import validate_config, ensure_output_directories, print_config


def print_banner(text: str):
    """Print a styled banner."""
    print("\n" + "="*70)
    print(text.center(70))
    print("="*70 + "\n")


def run_extraction(force: bool = False):
    """
    Run survey extraction step.
    
    Args:
        force: Force re-extraction even if chunks exist
    """
    print_banner("STEP 1: SURVEY EXTRACTION")
    
    from config import SURVEY_CHUNKS_DIR
    
    # Check if chunks already exist
    if not force and SURVEY_CHUNKS_DIR.exists():
        existing_files = list(SURVEY_CHUNKS_DIR.glob("survey_*.json"))
        if existing_files:
            print(f"⚠️  Survey chunks already exist ({len(existing_files)} files)")
            response = input("   Re-extract? (yes/no) [no]: ").strip().lower()
            if response != 'yes':
                print("   ⏭️  Skipping extraction step")
                return
    
    # Run extraction
    try:
        extract_surveys.main()
        print("✅ Extraction completed successfully\n")
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        sys.exit(1)


def run_summarization(llm_provider: str, batch_size: int, model_name: str = None):
    """
    Run summarization step.
    
    Args:
        llm_provider: LLM provider to use ("claude", "gemini", "ollama", or "both"/"all")
        batch_size: Batch size for processing
        model_name: Optional model name (for Ollama)
    """
    print_banner(f"STEP 2: SUMMARIZATION ({llm_provider.upper()})")
    
    try:
        if llm_provider in ['claude', 'both', 'all']:
            print("\n🤖 Running Claude Sonnet 4.5 summarization...")
            summarize_surveys.process_all_surveys('claude', batch_size)
        
        if llm_provider in ['gemini', 'both', 'all']:
            print("\n🤖 Running Gemini 3 Pro summarization...")
            summarize_surveys.process_all_surveys('gemini', batch_size)
        
        if llm_provider in ['ollama', 'all']:
            print(f"\n🤖 Running Ollama ({model_name or 'gpt-oss20b'}) summarization...")
            summarize_surveys.process_all_surveys('ollama', batch_size, model_name=model_name)
        
        print("✅ Summarization completed successfully\n")
    except Exception as e:
        print(f"❌ Summarization failed: {e}")
        print("   You may need to check your API keys and try again.")
        sys.exit(1)


def run_report_generation(llm_provider: str):
    """
    Run Markdown report generation step.
    
    Args:
        llm_provider: LLM provider to process ("claude", "gemini", "ollama", or "both"/"all")
    """
    print_banner(f"STEP 3: MARKDOWN REPORT GENERATION")
    
    try:
        if llm_provider in ['claude', 'both', 'all']:
            print("\n📝 Generating Claude reports...")
            generate_reports.process_all_summaries('claude')
        
        if llm_provider in ['gemini', 'both', 'all']:
            print("\n📝 Generating Gemini reports...")
            generate_reports.process_all_summaries('gemini')
        
        if llm_provider in ['ollama', 'all']:
            print("\n📝 Generating Ollama reports...")
            generate_reports.process_all_summaries('ollama')
        
        print("✅ Report generation completed successfully\n")
    except Exception as e:
        print(f"❌ Report generation failed: {e}")
        sys.exit(1)


def run_format_conversion(llm_provider: str, formats: list):
    """
    Run format conversion step.
    
    Args:
        llm_provider: LLM provider to process ("claude", "gemini", "ollama", or "both"/"all")
        formats: List of formats to generate
    """
    print_banner(f"STEP 4: FORMAT CONVERSION ({', '.join(formats).upper()})")
    
    try:
        if llm_provider in ['claude', 'both', 'all']:
            print("\n📄 Converting Claude reports...")
            convert_to_formats.process_all_markdown_files('claude', formats)
        
        if llm_provider in ['gemini', 'both', 'all']:
            print("\n📄 Converting Gemini reports...")
            convert_to_formats.process_all_markdown_files('gemini', formats)
        
        if llm_provider in ['ollama', 'all']:
            print("\n📄 Converting Ollama reports...")
            convert_to_formats.process_all_markdown_files('ollama', formats)
        
        print("✅ Format conversion completed successfully\n")
    except Exception as e:
        print(f"❌ Format conversion failed: {e}")
        if 'weasyprint' in str(e).lower():
            print("   Note: PDF generation requires system dependencies.")
            print("   See README.md for installation instructions.")
        sys.exit(1)


def print_summary(llm_provider: str):
    """Print final summary of generated files."""
    print_banner("PIPELINE COMPLETE!")
    
    from config import get_output_dir
    
    providers = []
    if llm_provider in ['claude', 'both', 'all']:
        providers.append('claude')
    if llm_provider in ['gemini', 'both', 'all']:
        providers.append('gemini')
    if llm_provider in ['ollama', 'all']:
        providers.append('ollama')
    
    for provider in providers:
        output_dir = get_output_dir(provider)
        
        if output_dir.exists():
            md_files = list(output_dir.glob("*.md"))
            html_files = list(output_dir.glob("*.html"))
            pdf_files = list(output_dir.glob("*.pdf"))
            
            print(f"📂 {provider.upper()} Reports:")
            print(f"   Location: {output_dir}")
            print(f"   Markdown: {len(md_files)} files")
            print(f"   HTML: {len(html_files)} files")
            print(f"   PDF: {len(pdf_files)} files")
            print()
    
    print("✨ All tasks completed successfully!")
    print("\nNext steps:")
    print("  - Review the generated reports in survey_summaries/")
    print("  - Open index.html files to browse all surveys")
    print("  - Share PDF files with stakeholders\n")


def main():
    """Main pipeline orchestrator."""
    parser = argparse.ArgumentParser(
        description="Run complete survey analysis pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full pipeline with both LLMs
  python run_analysis_pipeline.py
  
  # Run with only Claude
  python run_analysis_pipeline.py --llm claude
  
  # Skip extraction (if already done)
  python run_analysis_pipeline.py --skip-extraction
  
  # Only generate HTML (no PDF)
  python run_analysis_pipeline.py --formats html
  
  # Run specific steps only
  python run_analysis_pipeline.py --steps summarize report
        """
    )
    
    parser.add_argument(
        '--llm',
        choices=['claude', 'gemini', 'ollama', 'both', 'all'],
        default='both',
        help='LLM provider to use (default: both)'
    )
    
    parser.add_argument(
        '--model',
        type=str,
        help='Model name (for Ollama, default: gpt-oss20b)'
    )
    
    parser.add_argument(
        '--batch-size',
        type=int,
        default=10,
        help='Batch size for summarization (default: 10)'
    )
    
    parser.add_argument(
        '--formats',
        nargs='+',
        choices=['html', 'pdf'],
        default=['html', 'pdf'],
        help='Output formats to generate (default: html pdf)'
    )
    
    parser.add_argument(
        '--skip-extraction',
        action='store_true',
        help='Skip extraction step (use existing chunks)'
    )
    
    parser.add_argument(
        '--steps',
        nargs='+',
        choices=['extract', 'summarize', 'report', 'convert'],
        help='Run only specific steps (default: all steps)'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force re-extraction even if chunks exist'
    )
    
    args = parser.parse_args()
    
    # Determine which steps to run
    if args.steps:
        run_extract = 'extract' in args.steps
        run_summarize = 'summarize' in args.steps
        run_report = 'report' in args.steps
        run_convert = 'convert' in args.steps
    else:
        # Default: run all steps
        run_extract = not args.skip_extraction
        run_summarize = True
        run_report = True
        run_convert = True
    
    # Print configuration
    print_banner("SURVEY ANALYSIS PIPELINE")
    print("Configuration:")
    print(f"  LLM Provider: {args.llm}")
    print(f"  Batch Size: {args.batch_size}")
    print(f"  Output Formats: {', '.join(args.formats)}")
    print(f"  Steps: {'All' if not args.steps else ', '.join(args.steps)}")
    print()
    
    # Validate configuration
    if not validate_config():
        print("\n❌ Configuration validation failed. Please check:")
        print("   - ANTHROPIC_API_KEY environment variable")
        print("   - GOOGLE_API_KEY environment variable")
        print("   - Backup JSON file exists")
        sys.exit(1)
    
    # Ensure output directories exist
    ensure_output_directories()
    
    # Record start time
    start_time = time.time()
    
    # Run pipeline steps
    try:
        if run_extract:
            run_extraction(args.force)
        
        if run_summarize:
            run_summarization(args.llm, args.batch_size, args.model)
        
        if run_report:
            run_report_generation(args.llm)
        
        if run_convert:
            run_format_conversion(args.llm, args.formats)
        
        # Print final summary
        elapsed_time = time.time() - start_time
        minutes = int(elapsed_time // 60)
        seconds = int(elapsed_time % 60)
        
        print_summary(args.llm)
        print(f"⏱️  Total execution time: {minutes}m {seconds}s\n")
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

