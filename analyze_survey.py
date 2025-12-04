import json
import os
import re
import sys
from collections import defaultdict
import warnings

# Suppress warnings
warnings.filterwarnings("ignore")

try:
    import pandas as pd
    import matplotlib.pyplot as plt
    import matplotlib
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.cluster import KMeans
    import numpy as np
except ImportError as e:
    print(f"Error importing required libraries: {e}")
    print("Please ensure pandas, matplotlib, and scikit-learn are installed in 'mirai_db_analysis_py3.10'.")
    sys.exit(1)

# Configuration
BACKUP_FILE = 'backup-2025-11-14T03-19-14.json'
OUTPUT_DIR = 'analysis_results'

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Font setup for Japanese
def setup_japanese_font():
    # List of common Japanese fonts on macOS/Linux/Windows
    fonts = [
        'Hiragino Sans', 'Hiragino Kaku Gothic ProN', 'Yu Gothic', 'Meiryo', 
        'TakaoGothic', 'IPAGothic', 'Arial Unicode MS'
    ]
    found_font = None
    for font in fonts:
        try:
            # Check if font is available in matplotlib
            from matplotlib.font_manager import fontManager
            if any(f.name == font for f in fontManager.ttflist):
                found_font = font
                break
        except:
            continue
            
    if not found_font:
        # Fallback to system default or specific path if needed
        # On macOS, usually Hiragino is available even if not listed nicely sometimes
        found_font = 'Hiragino Sans' 
    
    plt.rcParams['font.family'] = found_font
    print(f"Using font: {found_font}")

setup_japanese_font()

def load_data(filepath):
    print(f"Loading {filepath}...")
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data

def get_questions(data):
    """
    Extract questions from interview_configs.
    Returns a dict: { config_id: { q_id: { 'text': text, 'topic': topic } } }
    """
    configs = {}
    for config in data['tables']['interview_configs']:
        c_id = config['id']
        questions = {}
        for q in config['questions']:
            # Clean text for matching
            q_text = q.get('mainQuestion') or q.get('text') or ""
            questions[q['id']] = {
                'text': q_text,
                'topic': q.get('topic', q['id']),
                'clean_text': q_text.strip()
            }
        configs[c_id] = {
            'title': config['title'],
            'questions': questions
        }
    return configs

def extract_answers(data, config_map):
    """
    Extract user answers mapped to questions.
    Heuristic: Match assistant message content to question text.
    """
    # Create a reverse lookup for question text -> (config_id, question_id)
    # Note: Question texts might be dynamic or contain templates, but we try exact/partial match first.
    # To be safer, we look at the session's config_id first.
    
    # Prepare config-specific text matchers
    config_text_map = {}
    for cid, cdata in config_map.items():
        config_text_map[cid] = []
        for qid, qdata in cdata['questions'].items():
            if qdata['clean_text']:
                config_text_map[cid].append((qid, qdata['clean_text']))
    
    answers = defaultdict(list) # key: (config_title, question_topic), value: [answers]
    
    # Group messages by session
    sessions = {s['id']: s for s in data['tables']['interview_sessions']}
    session_messages = defaultdict(list)
    
    # Sort messages by time to ensure order
    sorted_messages = sorted(data['tables']['messages'], key=lambda x: x['created_at'])
    
    for msg in sorted_messages:
        session_messages[msg['session_id']].append(msg)
        
    print(f"Processing {len(sessions)} sessions...")
    
    for session_id, msgs in session_messages.items():
        if session_id not in sessions:
            continue
        
        session = sessions[session_id]
        # Find which config this session belongs to
        # The session has 'slug', config has 'slug'. We need to map session -> config.
        # The backup schema for session doesn't show config_id directly, but has 'slug' and 'config_title'.
        # Config table has 'slug'.
        
        config_slug = session.get('slug')
        
        # Find config by slug
        matched_config = None
        matched_config_id = None
        
        # Search in config_map (which is by ID)
        # We need config list again or just search
        for cid, cdata in config_map.items():
            # We don't have slug in cdata, need to look at raw data or assume mapping
            # Let's look at raw data again or just use what we have.
            # Wait, get_questions only stored title. Let's iterate raw configs again?
            # Or just map by title since we have it.
            if cdata['title'] == session.get('config_title'):
                matched_config = cdata
                matched_config_id = cid
                break
        
        if not matched_config:
            continue

        # Now iterate messages and find Q&A pairs
        # Strategy: Assistant says Q -> User says A
        
        last_question_id = None
        
        for i, msg in enumerate(msgs):
            if msg['role'] == 'assistant':
                content = msg['content'].strip()
                # Try to find which question this is
                found_qid = None
                for qid, qtext in config_text_map[matched_config_id]:
                    # Simple check: is the question text contained in the message?
                    # The message might contain greeting + question.
                    if qtext and qtext in content:
                        found_qid = qid
                        break
                
                if found_qid:
                    last_question_id = found_qid
                else:
                    # Reset if we can't identify the question (avoid misattribution)
                    # Unless it's a follow-up? For now, strict match.
                    # Actually, follow-ups might be tricky.
                    pass
            
            elif msg['role'] == 'user':
                if last_question_id:
                    # This is an answer to last_question_id
                    q_topic = matched_config['questions'][last_question_id]['topic']
                    key = (matched_config['title'], q_topic)
                    answers[key].append(msg['content'])
                    
                    # Reset last_question_id so we don't attribute multiple user messages 
                    # to the same question unless we handle multi-turn. 
                    # Usually 1 Q -> 1 A.
                    last_question_id = None 

    return answers

def categorize_and_plot(answers_map):
    print("Categorizing and generating charts...")
    
    for (config_title, topic), texts in answers_map.items():
        if len(texts) < 5:
            # Too few answers to cluster
            continue
            
        print(f"Processing: {config_title} - {topic} ({len(texts)} answers)")
        
        # Vectorize (Char N-grams for Japanese support without tokenizer dependency)
        # 2-4 grams
        vectorizer = TfidfVectorizer(analyzer='char', ngram_range=(2, 4), min_df=2, max_features=1000)
        try:
            X = vectorizer.fit_transform(texts)
        except ValueError:
            # Likely empty vocabulary (texts too short or unique)
            continue
            
        # Cluster
        # Determine k: simple sqrt(n/2) or capped at 8
        num_clusters = min(8, max(3, int(len(texts) ** 0.5)))
        kmeans = KMeans(n_clusters=num_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(X)
        
        # Extract keywords for each cluster
        cluster_labels = {}
        feature_names = np.array(vectorizer.get_feature_names_out())
        
        # Get cluster centers
        ordered_centroids = kmeans.cluster_centers_.argsort()[:, ::-1]
        
        for i in range(num_clusters):
            # Get top terms
            top_terms = feature_names[ordered_centroids[i, :3]] # Top 3 terms
            # Create a label
            label = " / ".join(top_terms)
            cluster_labels[i] = label
            
        # Count
        counts = pd.Series(labels).value_counts()
        
        # Plot
        plt.figure(figsize=(10, 6))
        
        # Prepare data for plotting
        plot_labels = [cluster_labels[i] for i in counts.index]
        plot_values = counts.values
        
        # Create pie chart
        patches, texts, autotexts = plt.pie(
            plot_values, 
            labels=plot_labels, 
            autopct='%1.1f%%',
            startangle=90,
            counterclock=False
        )
        
        # Improve label visibility
        plt.setp(texts, size=9)
        plt.setp(autotexts, size=9, color="white", weight="bold")
        
        safe_topic = re.sub(r'[\\/*?:"<>|]', "_", topic)
        safe_title = re.sub(r'[\\/*?:"<>|]', "_", config_title)
        
        plt.title(f"{config_title}\n{topic}", fontsize=12)
        plt.axis('equal')
        
        filename = f"{OUTPUT_DIR}/chart_{safe_title}_{safe_topic}.png"
        plt.savefig(filename, bbox_inches='tight')
        plt.close()
        print(f"Saved {filename}")

def main():
    data = load_data(BACKUP_FILE)
    config_map = get_questions(data)
    answers_map = extract_answers(data, config_map)
    
    if not answers_map:
        print("No answers extracted. Check matching logic.")
        return

    categorize_and_plot(answers_map)
    print("Done.")

if __name__ == "__main__":
    main()
