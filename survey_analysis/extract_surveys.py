#!/usr/bin/env python3
"""
Extract surveys from large JSON backup file.

This script reads the backup JSON file and splits it into individual
survey files organized by interview_slug for easier processing.
"""

import json
import os
from pathlib import Path
from typing import Dict, List
from collections import defaultdict
from tqdm import tqdm


def load_json_file(file_path: str) -> dict:
    """Load JSON file with progress indication."""
    print(f"📂 Loading JSON file: {file_path}")
    file_size = os.path.getsize(file_path)
    print(f"   File size: {file_size / (1024 * 1024):.1f} MB")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print("✅ JSON file loaded successfully")
    return data


def extract_survey_configs(data: dict) -> Dict[str, dict]:
    """Extract interview configurations indexed by slug."""
    configs = data.get('tables', {}).get('interview_configs', [])
    print(f"📋 Found {len(configs)} interview configurations")
    
    config_map = {}
    for config in configs:
        slug = config.get('slug')
        if slug:
            config_map[slug] = {
                'id': config.get('id'),
                'slug': slug,
                'title': config.get('title'),
                'description': config.get('description'),
                'questions': config.get('questions', []),
                'status': config.get('status'),
                'created_at': config.get('created_at'),
            }
    
    return config_map


def extract_sessions_by_survey(data: dict) -> Dict[str, List[dict]]:
    """Group sessions by interview_slug."""
    sessions = data.get('tables', {}).get('interview_sessions', [])
    print(f"💬 Found {len(sessions)} interview sessions")
    
    sessions_by_slug = defaultdict(list)
    for session in sessions:
        slug = session.get('slug')
        if slug:
            sessions_by_slug[slug].append(session)
    
    return dict(sessions_by_slug)


def extract_messages(data: dict) -> Dict[str, List[dict]]:
    """Group messages by session_id."""
    messages = data.get('tables', {}).get('messages', [])
    print(f"💭 Found {len(messages)} messages")
    
    messages_by_session = defaultdict(list)
    for msg in messages:
        session_id = msg.get('session_id')
        if session_id:
            messages_by_session[session_id].append(msg)
    
    return dict(messages_by_session)


def compile_survey_data(
    config_map: Dict[str, dict],
    sessions_by_slug: Dict[str, List[dict]],
    messages_by_session: Dict[str, List[dict]]
) -> Dict[str, dict]:
    """Compile complete survey data with configs, sessions, and messages."""
    survey_data = {}
    
    for slug, config in config_map.items():
        sessions = sessions_by_slug.get(slug, [])
        
        # Add messages to each session
        sessions_with_messages = []
        total_messages = 0
        
        for session in sessions:
            session_id = session.get('id')
            session_messages = messages_by_session.get(session_id, [])
            
            # Sort messages by timestamp
            session_messages.sort(key=lambda x: x.get('timestamp', ''))
            
            sessions_with_messages.append({
                **session,
                'messages': session_messages
            })
            total_messages += len(session_messages)
        
        survey_data[slug] = {
            'config': config,
            'sessions': sessions_with_messages,
            'stats': {
                'num_sessions': len(sessions_with_messages),
                'num_messages': total_messages,
                'num_questions': len(config.get('questions', []))
            }
        }
    
    return survey_data


def save_survey_chunks(survey_data: Dict[str, dict], output_dir: str):
    """Save each survey to a separate JSON file."""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True, parents=True)
    
    print(f"\n📝 Saving survey chunks to: {output_dir}")
    
    for slug, data in tqdm(survey_data.items(), desc="Saving surveys"):
        output_file = output_path / f"survey_{slug}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        stats = data['stats']
        print(f"   ✅ {slug}: {stats['num_sessions']} sessions, "
              f"{stats['num_messages']} messages → {output_file.name}")
    
    return output_path


def print_summary(survey_data: Dict[str, dict]):
    """Print summary statistics."""
    print("\n" + "="*70)
    print("EXTRACTION SUMMARY")
    print("="*70)
    
    total_sessions = sum(d['stats']['num_sessions'] for d in survey_data.values())
    total_messages = sum(d['stats']['num_messages'] for d in survey_data.values())
    
    print(f"Total surveys: {len(survey_data)}")
    print(f"Total sessions: {total_sessions:,}")
    print(f"Total messages: {total_messages:,}")
    
    print("\nSurvey breakdown:")
    for slug, data in sorted(survey_data.items()):
        title = data['config']['title']
        stats = data['stats']
        print(f"  • {title} ({slug})")
        print(f"    - Sessions: {stats['num_sessions']:,}")
        print(f"    - Messages: {stats['num_messages']:,}")
        print(f"    - Questions: {stats['num_questions']}")
    
    print("="*70 + "\n")


def main():
    """Main extraction pipeline."""
    # Configuration
    JSON_FILE = "../backup-2025-11-14T03-19-14.json"
    OUTPUT_DIR = "./survey_chunks"
    
    print("\n" + "="*70)
    print("SURVEY DATA EXTRACTION")
    print("="*70 + "\n")
    
    # Step 1: Load JSON
    try:
        data = load_json_file(JSON_FILE)
    except FileNotFoundError:
        print(f"❌ Error: File not found: {JSON_FILE}")
        return
    except Exception as e:
        print(f"❌ Error loading JSON: {e}")
        return
    
    # Step 2: Extract data
    print("\n📊 Extracting data...")
    config_map = extract_survey_configs(data)
    sessions_by_slug = extract_sessions_by_survey(data)
    messages_by_session = extract_messages(data)
    
    # Step 3: Compile survey data
    print("\n🔨 Compiling survey data...")
    survey_data = compile_survey_data(config_map, sessions_by_slug, messages_by_session)
    
    # Step 4: Save chunks
    output_path = save_survey_chunks(survey_data, OUTPUT_DIR)
    
    # Step 5: Print summary
    print_summary(survey_data)
    
    print(f"✨ Extraction complete! Files saved to: {output_path}")
    print(f"\nNext step: Run summarization with:")
    print(f"  python summarize_surveys.py")


if __name__ == "__main__":
    main()












