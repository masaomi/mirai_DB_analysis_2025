import json
import os
import shutil
import re
import hashlib
from typing import List, Dict, Optional, Tuple, Set
from collections import Counter, defaultdict
from datetime import datetime
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from tqdm import tqdm

# Configuration
JSON_FILE_PATH = "../backup-2025-11-14T03-19-14.json"
CHROMA_DB_DIR = "./chroma_db"
COLLECTION_NAME = "survey_responses"
BATCH_SIZE = 1000
# Use multilingual model for better Japanese support
EMBEDDING_MODEL = "intfloat/multilingual-e5-base"  # or "all-MiniLM-L6-v2" for speed
STATISTICS_FILE = "./ingestion_statistics.json"

# Quality filter settings
MIN_ANSWER_LENGTH = 5  # Minimum characters for Japanese
MEANINGLESS_ANSWERS = ["はい", "いいえ", "わからない", "不明", "なし", "特になし", "-", ""]

def parse_timestamp(timestamp_str: str) -> Dict[str, any]:
    """
    Parse timestamp string and extract date-related metadata.
    """
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return {
            "timestamp_unix": int(dt.timestamp()),
            "date": dt.strftime("%Y-%m-%d"),
            "year_month": dt.strftime("%Y-%m"),
            "day_of_week": dt.strftime("%A"),
            "hour": dt.hour,
            "year": dt.year,
            "month": dt.month,
            "day": dt.day
        }
    except Exception as e:
        print(f"Warning: Failed to parse timestamp '{timestamp_str}': {e}")
        return {
            "timestamp_unix": 0,
            "date": "unknown",
            "year_month": "unknown",
            "day_of_week": "unknown",
            "hour": 0,
            "year": 0,
            "month": 0,
            "day": 0
        }

def calculate_response_quality(text: str) -> Tuple[float, str]:
    """
    Calculate response quality score based on content characteristics.
    Returns: (quality_score, quality_label)
    
    Quality criteria:
    - Length (longer = better, but diminishing returns)
    - Character variety (not just symbols/numbers)
    - Sentence structure
    """
    if not text or len(text) < MIN_ANSWER_LENGTH:
        return 0.0, "very_low"
    
    # Check if text is meaningful (not just symbols or numbers)
    alphanumeric_ratio = len(re.findall(r'[a-zA-Z0-9ぁ-んァ-ヶー一-龯]', text)) / len(text)
    if alphanumeric_ratio < 0.3:
        return 0.2, "low"
    
    # Length score (0-40 points)
    length_score = min(len(text) / 500.0, 1.0) * 40
    
    # Sentence count (0-30 points)
    sentence_count = len(re.findall(r'[。！？\.\!\?]', text))
    sentence_score = min(sentence_count / 3.0, 1.0) * 30
    
    # Character variety (0-30 points)
    unique_chars = len(set(text))
    variety_score = min(unique_chars / 50.0, 1.0) * 30
    
    total_score = (length_score + sentence_score + variety_score) / 100.0
    
    # Categorize quality
    if total_score >= 0.7:
        quality_label = "high"
    elif total_score >= 0.5:
        quality_label = "medium"
    elif total_score >= 0.3:
        quality_label = "low"
    else:
        quality_label = "very_low"
    
    return round(total_score, 2), quality_label

def is_valid_response(text: str) -> bool:
    """
    Check if response is valid and meaningful.
    """
    if not text or len(text) < MIN_ANSWER_LENGTH:
        return False
    
    # Check against meaningless answers
    text_normalized = text.strip().lower()
    if text_normalized in [ans.lower() for ans in MEANINGLESS_ANSWERS]:
        return False
    
    # Check if it's only symbols or numbers
    alphanumeric_count = len(re.findall(r'[a-zA-Z0-9ぁ-んァ-ヶー一-龯]', text))
    if alphanumeric_count < 3:  # At least 3 meaningful characters
        return False
    
    return True

def analyze_sentiment(text: str) -> Tuple[float, str, Dict[str, int]]:
    """
    Analyze sentiment of text using dictionary-based approach.
    Returns: (sentiment_score, sentiment_label, word_counts)
    
    Score range: -1.0 (very negative) to +1.0 (very positive)
    """
    text_lower = text.lower()
    
    # Extended sentiment dictionaries with weights
    positive_words = {
        # Strong positive (weight: 2)
        "素晴らしい": 2, "最高": 2, "大賛成": 2, "感動": 2, "喜ばしい": 2,
        # Moderate positive (weight: 1)
        "賛成": 1, "良い": 1, "期待": 1, "希望": 1, "支持": 1, "好ましい": 1, 
        "必要": 1, "重要": 1, "適切": 1, "有効": 1, "役立つ": 1, "効果的": 1,
        "優れた": 1, "満足": 1, "嬉しい": 1, "助かる": 1, "安心": 1, "便利": 1,
        "ありがた": 1, "歓迎": 1, "前向き": 1, "ポジティブ": 1
    }
    
    negative_words = {
        # Strong negative (weight: 2)
        "最悪": 2, "大反対": 2, "許せない": 2, "憤り": 2, "怒り": 2,
        # Moderate negative (weight: 1)
        "反対": 1, "悪い": 1, "問題": 1, "懸念": 1, "不安": 1, "不要": 1, 
        "無駄": 1, "疑問": 1, "心配": 1, "危険": 1, "困る": 1, "難しい": 1,
        "不満": 1, "残念": 1, "不適切": 1, "不十分": 1, "不信": 1, "不公平": 1,
        "ネガティブ": 1, "否定的": 1
    }
    
    # Neutral/qualifying words
    neutral_words = ["わからない", "不明", "どちらとも", "中立", "判断できない"]
    
    # Count sentiment words
    positive_score = 0
    negative_score = 0
    neutral_count = 0
    
    positive_count = 0
    negative_count = 0
    
    for word, weight in positive_words.items():
        count = text_lower.count(word)
        if count > 0:
            positive_score += count * weight
            positive_count += count
    
    for word, weight in negative_words.items():
        count = text_lower.count(word)
        if count > 0:
            negative_score += count * weight
            negative_count += count
    
    for word in neutral_words:
        if word in text_lower:
            neutral_count += 1
    
    # Calculate overall sentiment score
    total_sentiment_words = positive_score + negative_score
    
    if total_sentiment_words == 0:
        # No sentiment words found
        if neutral_count > 0:
            sentiment_score = 0.0
            sentiment_label = "neutral"
        else:
            sentiment_score = 0.0
            sentiment_label = "unknown"
    else:
        # Calculate normalized score (-1 to +1)
        sentiment_score = (positive_score - negative_score) / (positive_score + negative_score)
        
        # Determine label
        if sentiment_score >= 0.5:
            sentiment_label = "positive"
        elif sentiment_score >= 0.2:
            sentiment_label = "slightly_positive"
        elif sentiment_score >= -0.2:
            sentiment_label = "neutral"
        elif sentiment_score >= -0.5:
            sentiment_label = "slightly_negative"
        else:
            sentiment_label = "negative"
    
    word_counts = {
        "positive_words": positive_count,
        "negative_words": negative_count,
        "neutral_words": neutral_count
    }
    
    return round(sentiment_score, 3), sentiment_label, word_counts

def detect_keywords(text: str) -> Dict[str, bool]:
    """
    Detect presence of important keywords in text.
    Returns flags for different keyword categories.
    """
    text_lower = text.lower()
    
    # Positive sentiment keywords
    positive_keywords = ["賛成", "良い", "素晴らしい", "期待", "希望", "支持", "好ましい", "必要", "重要"]
    has_positive = any(keyword in text_lower for keyword in positive_keywords)
    
    # Negative sentiment keywords
    negative_keywords = ["反対", "悪い", "問題", "懸念", "不安", "反対", "不要", "無駄"]
    has_negative = any(keyword in text_lower for keyword in negative_keywords)
    
    # Policy-related keywords
    policy_keywords = ["法案", "政策", "制度", "議員", "国会", "法律", "規制"]
    has_policy = any(keyword in text_lower for keyword in policy_keywords)
    
    return {
        "has_positive_keywords": has_positive,
        "has_negative_keywords": has_negative,
        "has_policy_keywords": has_policy
    }

def determine_question_type(question: str) -> str:
    """
    Determine the type of question based on its content.
    """
    question_lower = question.lower()
    
    # Check for yes/no questions
    if any(q in question_lower for q in ["ですか", "ますか", "はい", "いいえ"]):
        return "yes_no"
    
    # Check for rating/scale questions
    if any(q in question_lower for q in ["点数", "評価", "スコア", "1から", "段階"]):
        return "rating"
    
    # Check for multiple choice
    if any(q in question_lower for q in ["選択", "どれ", "いずれ"]):
        return "multiple_choice"
    
    # Default to open-ended
    return "open_ended"

def calculate_text_hash(text: str) -> str:
    """
    Calculate a hash of the text for exact duplicate detection.
    """
    normalized_text = text.strip().lower()
    return hashlib.md5(normalized_text.encode('utf-8')).hexdigest()

def calculate_similarity_hash(text: str) -> str:
    """
    Calculate a fuzzy hash for near-duplicate detection.
    Removes punctuation and extra whitespace.
    """
    # Remove punctuation and normalize whitespace
    normalized = re.sub(r'[^\w\s]', '', text.lower())
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    return hashlib.md5(normalized.encode('utf-8')).hexdigest()

def detect_duplicates(documents: List[Document]) -> Tuple[List[Document], Dict]:
    """
    Detect and mark duplicate/similar responses.
    Returns: (documents_with_duplicate_info, duplicate_statistics)
    """
    print("\nDetecting duplicate and similar responses...")
    
    # Track exact duplicates
    exact_hash_map: Dict[str, List[int]] = defaultdict(list)
    # Track similar responses (fuzzy matching)
    fuzzy_hash_map: Dict[str, List[int]] = defaultdict(list)
    
    # First pass: calculate hashes
    for i, doc in enumerate(documents):
        answer = doc.metadata.get("answer", "")
        
        # Exact duplicate detection
        exact_hash = calculate_text_hash(answer)
        exact_hash_map[exact_hash].append(i)
        
        # Fuzzy duplicate detection
        fuzzy_hash = calculate_similarity_hash(answer)
        fuzzy_hash_map[fuzzy_hash].append(i)
    
    # Count duplicates
    exact_duplicates = sum(1 for indices in exact_hash_map.values() if len(indices) > 1)
    fuzzy_duplicates = sum(1 for indices in fuzzy_hash_map.values() if len(indices) > 1)
    
    # Assign duplicate group IDs
    duplicate_group_counter = 0
    fuzzy_group_counter = 0
    
    # Second pass: add duplicate information to documents
    for exact_hash, indices in exact_hash_map.items():
        if len(indices) > 1:
            duplicate_group_counter += 1
            for idx in indices:
                documents[idx].metadata["is_exact_duplicate"] = True
                documents[idx].metadata["exact_duplicate_group_id"] = f"exact_{duplicate_group_counter}"
                documents[idx].metadata["exact_duplicate_count"] = len(indices)
    
    for fuzzy_hash, indices in fuzzy_hash_map.items():
        if len(indices) > 1:
            fuzzy_group_counter += 1
            for idx in indices:
                # Only mark as fuzzy duplicate if not already an exact duplicate
                if not documents[idx].metadata.get("is_exact_duplicate", False):
                    documents[idx].metadata["is_fuzzy_duplicate"] = True
                    documents[idx].metadata["fuzzy_duplicate_group_id"] = f"fuzzy_{fuzzy_group_counter}"
                    documents[idx].metadata["fuzzy_duplicate_count"] = len(indices)
    
    # Mark non-duplicates
    for doc in documents:
        if "is_exact_duplicate" not in doc.metadata:
            doc.metadata["is_exact_duplicate"] = False
        if "is_fuzzy_duplicate" not in doc.metadata:
            doc.metadata["is_fuzzy_duplicate"] = False
    
    # Compile statistics
    stats = {
        "total_exact_duplicate_groups": duplicate_group_counter,
        "total_fuzzy_duplicate_groups": fuzzy_group_counter,
        "documents_with_exact_duplicates": sum(1 for doc in documents if doc.metadata.get("is_exact_duplicate")),
        "documents_with_fuzzy_duplicates": sum(1 for doc in documents if doc.metadata.get("is_fuzzy_duplicate")),
        "unique_responses": len(documents) - sum(1 for doc in documents if doc.metadata.get("is_exact_duplicate"))
    }
    
    print(f"  Exact duplicate groups: {stats['total_exact_duplicate_groups']}")
    print(f"  Documents in exact duplicate groups: {stats['documents_with_exact_duplicates']}")
    print(f"  Fuzzy duplicate groups: {stats['total_fuzzy_duplicate_groups']}")
    print(f"  Documents in fuzzy duplicate groups: {stats['documents_with_fuzzy_duplicates']}")
    print(f"  Unique responses: {stats['unique_responses']}")
    
    return documents, stats

def load_and_process_data(file_path: str) -> Tuple[List[Document], Dict]:
    """
    Load JSON data and extract user responses with enhanced metadata.
    Returns: (documents, statistics)
    """
    print(f"Loading data from {file_path}...")
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Load tables
    tables = data.get("tables", {})
    messages = tables.get("messages", [])
    configs = tables.get("interview_configs", [])
    sessions_data = tables.get("interview_sessions", [])
    
    if not messages:
        raise ValueError("No messages found in data")
        
    print(f"Found {len(messages)} messages")
    print(f"Found {len(configs)} interview configs")
    print(f"Found {len(sessions_data)} sessions")

    # Create lookup maps
    config_map = {cfg.get("slug"): cfg for cfg in configs}
    session_to_slug = {s.get("id"): s.get("slug") for s in sessions_data}

    # Group messages by session_id
    sessions: Dict[str, List[Dict]] = {}
    for msg in messages:
        session_id = msg.get("session_id")
        if not session_id:
            continue
        if session_id not in sessions:
            sessions[session_id] = []
        sessions[session_id].append(msg)

    print(f"Grouped messages into {len(sessions)} sessions")

    # Count responses per topic for statistics
    topic_response_counts = Counter()

    documents = []
    skipped_count = 0
    quality_distribution = Counter()
    sentiment_distribution = Counter()
    all_timestamps = []
    
    # Process each session with progress bar
    for session_id, session_msgs in tqdm(sessions.items(), desc="Processing sessions"):
        # Get topic information
        slug = session_to_slug.get(session_id)
        config = config_map.get(slug, {})
        topic_name = config.get("title", "Unknown Topic")
        topic_slug = config.get("slug", "unknown")
        
        # Sort messages by timestamp
        session_msgs.sort(key=lambda x: x.get("timestamp", ""))
        
        # Track response order within session
        response_order = 0
        
        for i in range(len(session_msgs)):
            msg = session_msgs[i]
            
            # We are interested in USER messages
            if msg.get("role") == "user":
                user_content = msg.get("content", "").strip()
                
                # Enhanced validation
                if not is_valid_response(user_content):
                    skipped_count += 1
                    continue
                
                response_order += 1
                
                # Find the preceding assistant message (Question)
                question = "Unknown Question"
                if i > 0 and session_msgs[i-1].get("role") == "assistant":
                    question = session_msgs[i-1].get("content", "").strip()
                
                # Parse timestamp
                timestamp_str = msg.get("timestamp", "")
                date_info = parse_timestamp(timestamp_str)
                all_timestamps.append(date_info["date"])
                
                # Calculate quality score
                quality_score, quality_label = calculate_response_quality(user_content)
                quality_distribution[quality_label] += 1
                
                # Analyze sentiment
                sentiment_score, sentiment_label, sentiment_word_counts = analyze_sentiment(user_content)
                sentiment_distribution[sentiment_label] += 1
                
                # Detect keywords
                keyword_flags = detect_keywords(user_content)
                
                # Determine question type
                question_type = determine_question_type(question)
                
                # Count words (approximation for Japanese)
                word_count = len(user_content)  # For Japanese, character count is reasonable
                
                # Create document content - using answer only for better retrieval
                page_content = user_content
                
                # Enhanced metadata
                metadata = {
                    # Original fields
                    "session_id": session_id,
                    "timestamp": timestamp_str,
                    "role": "user",
                    "type": "survey_response",
                    "topic": topic_name,
                    "topic_slug": topic_slug,
                    
                    # Separated question and answer
                    "question": question,
                    "answer": user_content,
                    
                    # Length metrics
                    "answer_length": len(user_content),
                    "answer_word_count": word_count,
                    
                    # Date/time information
                    "date": date_info["date"],
                    "year_month": date_info["year_month"],
                    "day_of_week": date_info["day_of_week"],
                    "timestamp_unix": date_info["timestamp_unix"],
                    "year": date_info["year"],
                    "month": date_info["month"],
                    "day": date_info["day"],
                    "hour": date_info["hour"],
                    
                    # Quality metrics
                    "response_quality": quality_label,
                    "quality_score": quality_score,
                    
                    # Sentiment analysis
                    "sentiment_score": sentiment_score,
                    "sentiment_label": sentiment_label,
                    "sentiment_positive_words": sentiment_word_counts["positive_words"],
                    "sentiment_negative_words": sentiment_word_counts["negative_words"],
                    "sentiment_neutral_words": sentiment_word_counts["neutral_words"],
                    
                    # Keyword flags
                    "has_positive_keywords": keyword_flags["has_positive_keywords"],
                    "has_negative_keywords": keyword_flags["has_negative_keywords"],
                    "has_policy_keywords": keyword_flags["has_policy_keywords"],
                    
                    # Question/response metadata
                    "question_type": question_type,
                    "session_response_order": response_order,
                }
                
                # Update topic count
                topic_response_counts[topic_name] += 1
                metadata["topic_response_count"] = topic_response_counts[topic_name]
                
                documents.append(Document(page_content=page_content, metadata=metadata))

    print(f"\nCreated {len(documents)} documents from survey responses")
    print(f"Skipped {skipped_count} invalid/low-quality responses")
    
    # Calculate average sentiment score
    sentiment_scores = [doc.metadata["sentiment_score"] for doc in documents]
    avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
    
    # Compile statistics
    statistics = {
        "total_documents": len(documents),
        "skipped_documents": skipped_count,
        "ingestion_timestamp": datetime.now().isoformat(),
        "topic_distribution": dict(topic_response_counts),
        "quality_distribution": dict(quality_distribution),
        "sentiment_distribution": dict(sentiment_distribution),
        "average_sentiment_score": round(avg_sentiment, 3),
        "date_range": {
            "start": min(all_timestamps) if all_timestamps else "unknown",
            "end": max(all_timestamps) if all_timestamps else "unknown"
        },
        "average_answer_length": sum(len(doc.metadata["answer"]) for doc in documents) / len(documents) if documents else 0,
        "total_sessions": len(sessions),
        "total_topics": len(topic_response_counts)
    }
    
    return documents, statistics

def print_statistics(documents: List[Document], statistics: Dict):
    """Print enhanced statistics about the processed documents."""
    print("\n" + "="*50)
    print("DATA STATISTICS")
    print("="*50)
    print(f"Total documents: {statistics['total_documents']:,}")
    print(f"Skipped documents: {statistics['skipped_documents']:,}")
    print(f"Total sessions: {statistics['total_sessions']:,}")
    print(f"Total topics: {statistics['total_topics']:,}")
    
    # Date range
    print(f"\nDate range:")
    print(f"  Start: {statistics['date_range']['start']}")
    print(f"  End: {statistics['date_range']['end']}")
    
    # Length distribution
    lengths = [len(doc.page_content) for doc in documents]
    print(f"\nAnswer length:")
    print(f"  Average: {statistics['average_answer_length']:.1f} characters")
    print(f"  Min: {min(lengths)} characters")
    print(f"  Max: {max(lengths)} characters")
    
    # Quality distribution
    print(f"\nQuality distribution:")
    for quality, count in sorted(statistics['quality_distribution'].items()):
        percentage = (count / statistics['total_documents']) * 100
        print(f"  {quality}: {count:,} ({percentage:.1f}%)")
    
    # Sentiment distribution
    print(f"\nSentiment distribution:")
    avg_sentiment = statistics.get('average_sentiment_score', 0)
    print(f"  Average sentiment score: {avg_sentiment:.3f}")
    for sentiment, count in sorted(statistics.get('sentiment_distribution', {}).items()):
        percentage = (count / statistics['total_documents']) * 100
        print(f"  {sentiment}: {count:,} ({percentage:.1f}%)")
    
    # Topic distribution (top 10)
    print(f"\nTop 10 Topics:")
    topic_items = sorted(statistics['topic_distribution'].items(), key=lambda x: x[1], reverse=True)
    for topic, count in topic_items[:10]:
        percentage = (count / statistics['total_documents']) * 100
        print(f"  {topic}: {count:,} ({percentage:.1f}%)")
    
    if len(topic_items) > 10:
        print(f"  ... and {len(topic_items) - 10} more topics")
    
    # Keyword statistics
    positive_count = sum(1 for doc in documents if doc.metadata.get("has_positive_keywords"))
    negative_count = sum(1 for doc in documents if doc.metadata.get("has_negative_keywords"))
    policy_count = sum(1 for doc in documents if doc.metadata.get("has_policy_keywords"))
    
    print(f"\nKeyword presence:")
    print(f"  Positive keywords: {positive_count:,} ({positive_count/len(documents)*100:.1f}%)")
    print(f"  Negative keywords: {negative_count:,} ({negative_count/len(documents)*100:.1f}%)")
    print(f"  Policy keywords: {policy_count:,} ({policy_count/len(documents)*100:.1f}%)")
    
    # Question type distribution
    question_types = Counter(doc.metadata.get("question_type") for doc in documents)
    print(f"\nQuestion type distribution:")
    for qtype, count in question_types.most_common():
        percentage = (count / len(documents)) * 100
        print(f"  {qtype}: {count:,} ({percentage:.1f}%)")
    
    # Duplicate statistics (if available)
    if "duplicate_statistics" in statistics:
        dup_stats = statistics["duplicate_statistics"]
        print(f"\nDuplicate detection:")
        print(f"  Exact duplicate groups: {dup_stats.get('total_exact_duplicate_groups', 0):,}")
        print(f"  Docs with exact duplicates: {dup_stats.get('documents_with_exact_duplicates', 0):,}")
        print(f"  Fuzzy duplicate groups: {dup_stats.get('total_fuzzy_duplicate_groups', 0):,}")
        print(f"  Docs with fuzzy duplicates: {dup_stats.get('documents_with_fuzzy_duplicates', 0):,}")
        print(f"  Unique responses: {dup_stats.get('unique_responses', 0):,}")
    
    print("="*50 + "\n")

def save_statistics(statistics: Dict, file_path: str):
    """Save statistics to JSON file."""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(statistics, f, ensure_ascii=False, indent=2)
        print(f"✅ Statistics saved to {file_path}")
    except Exception as e:
        print(f"⚠️  Warning: Failed to save statistics: {e}")

def create_vector_store_in_batches(documents: List[Document], 
                                   embeddings,
                                   batch_size: int = BATCH_SIZE):
    """Process documents in batches to avoid memory issues."""
    print(f"Processing {len(documents):,} documents in batches of {batch_size:,}...")
    
    # First batch - create the vector store
    first_batch = documents[:batch_size]
    vector_store = Chroma.from_documents(
        documents=first_batch,
        embedding=embeddings,
        persist_directory=CHROMA_DB_DIR,
        collection_name=COLLECTION_NAME
    )
    print(f"Created vector store with first {len(first_batch)} documents")
    
    # Remaining batches - add to existing store
    for i in range(batch_size, len(documents), batch_size):
        batch = documents[i:i+batch_size]
        vector_store.add_documents(batch)
        progress = min(i+batch_size, len(documents))
        print(f"  Processed {progress:,}/{len(documents):,} documents ({(progress/len(documents)*100):.1f}%)")
    
    return vector_store

def main():
    print("\n" + "="*50)
    print("SURVEY RAG DATA INGESTION (Enhanced)")
    print("="*50 + "\n")
    
    # 1. Load Documents with enhanced metadata
    try:
        documents, statistics = load_and_process_data(JSON_FILE_PATH)
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        import traceback
        traceback.print_exc()
        return

    if not documents:
        print("❌ No documents to ingest.")
        return

    # 2. Detect duplicates and similar responses
    documents, duplicate_stats = detect_duplicates(documents)
    statistics["duplicate_statistics"] = duplicate_stats

    # 3. Print statistics
    print_statistics(documents, statistics)

    # 4. Save statistics to JSON
    save_statistics(statistics, STATISTICS_FILE)

    # 4. Handle existing vector store
    if os.path.exists(CHROMA_DB_DIR):
        print(f"⚠️  Warning: Vector store already exists at {CHROMA_DB_DIR}")
        response = input("Do you want to overwrite it? (yes/no): ").strip().lower()
        if response == 'yes':
            print("Removing existing vector store...")
            shutil.rmtree(CHROMA_DB_DIR)
        else:
            print("Aborted. Existing vector store preserved.")
            return

    # 5. Initialize Embeddings
    print(f"\nInitializing Embeddings ({EMBEDDING_MODEL})...")
    print("⏳ This may take a moment on first run (downloading model)...")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    # 6. Create Vector Store in batches
    print(f"\nCreating Vector Store in {CHROMA_DB_DIR}...")
    vector_store = create_vector_store_in_batches(documents, embeddings)
    
    print(f"\n✅ Data ingestion complete!")
    print(f"📁 Vector store saved to {CHROMA_DB_DIR}")
    print(f"📊 Total documents indexed: {len(documents):,}")
    print(f"📈 Statistics saved to {STATISTICS_FILE}")
    print("\nYou can now run the Streamlit app: streamlit run app.py\n")

if __name__ == "__main__":
    main()

