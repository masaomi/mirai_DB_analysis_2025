import json
import os
import shutil
from typing import List, Dict, Optional
from collections import Counter
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

def load_and_process_data(file_path: str) -> List[Document]:
    """
    Load JSON data and extract user responses with context.
    Includes topic information from interview_configs.
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
    # Sessions use 'slug' to link to configs, not 'config_id'
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

    documents = []
    skipped_count = 0
    
    # Process each session with progress bar
    for session_id, session_msgs in tqdm(sessions.items(), desc="Processing sessions"):
        # Get topic information
        slug = session_to_slug.get(session_id)
        config = config_map.get(slug, {})
        topic_name = config.get("title", "Unknown Topic")
        topic_slug = config.get("slug", "unknown")
        
        # Sort messages by timestamp
        session_msgs.sort(key=lambda x: x.get("timestamp", ""))
        
        for i in range(len(session_msgs)):
            msg = session_msgs[i]
            
            # We are interested in USER messages
            if msg.get("role") == "user":
                user_content = msg.get("content", "").strip()
                
                # Skip empty or very short responses
                if not user_content or len(user_content) < 2:
                    skipped_count += 1
                    continue
                
                # Find the preceding assistant message (Question)
                question = "Unknown Question"
                if i > 0 and session_msgs[i-1].get("role") == "assistant":
                    question = session_msgs[i-1].get("content", "").strip()
                
                # Create document content
                page_content = f"Question: {question}\nAnswer: {user_content}"
                
                metadata = {
                    "session_id": session_id,
                    "timestamp": msg.get("timestamp"),
                    "role": "user",
                    "type": "survey_response",
                    "topic": topic_name,
                    "topic_slug": topic_slug,
                    "answer_length": len(user_content)
                }
                
                documents.append(Document(page_content=page_content, metadata=metadata))

    print(f"\nCreated {len(documents)} documents from survey responses")
    print(f"Skipped {skipped_count} empty/short responses")
    return documents

def print_statistics(documents: List[Document]):
    """Print statistics about the processed documents."""
    print("\n" + "="*50)
    print("DATA STATISTICS")
    print("="*50)
    print(f"Total documents: {len(documents):,}")
    
    # Length distribution
    lengths = [len(doc.page_content) for doc in documents]
    print(f"\nContent length:")
    print(f"  Average: {sum(lengths)/len(lengths):.1f} characters")
    print(f"  Min: {min(lengths)} characters")
    print(f"  Max: {max(lengths)} characters")
    
    # Answer length distribution
    answer_lengths = [doc.metadata.get("answer_length", 0) for doc in documents]
    print(f"\nAnswer length:")
    print(f"  Average: {sum(answer_lengths)/len(answer_lengths):.1f} characters")
    
    # Topic distribution
    topics = [doc.metadata.get("topic", "Unknown") for doc in documents]
    topic_counts = Counter(topics)
    print(f"\nTopic distribution:")
    for topic, count in topic_counts.most_common():
        percentage = (count / len(documents)) * 100
        print(f"  {topic}: {count:,} ({percentage:.1f}%)")
    print("="*50 + "\n")

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
    print("SURVEY RAG DATA INGESTION")
    print("="*50 + "\n")
    
    # 1. Load Documents
    try:
        documents = load_and_process_data(JSON_FILE_PATH)
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return

    if not documents:
        print("❌ No documents to ingest.")
        return

    # 2. Print statistics
    print_statistics(documents)

    # 3. Handle existing vector store
    if os.path.exists(CHROMA_DB_DIR):
        print(f"⚠️  Warning: Vector store already exists at {CHROMA_DB_DIR}")
        response = input("Do you want to overwrite it? (yes/no): ").strip().lower()
        if response == 'yes':
            print("Removing existing vector store...")
            shutil.rmtree(CHROMA_DB_DIR)
        else:
            print("Aborted. Existing vector store preserved.")
            return

    # 4. Initialize Embeddings
    print(f"\nInitializing Embeddings ({EMBEDDING_MODEL})...")
    print("⏳ This may take a moment on first run (downloading model)...")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    # 5. Create Vector Store in batches
    print(f"\nCreating Vector Store in {CHROMA_DB_DIR}...")
    vector_store = create_vector_store_in_batches(documents, embeddings)
    
    print(f"\n✅ Data ingestion complete!")
    print(f"📁 Vector store saved to {CHROMA_DB_DIR}")
    print(f"📊 Total documents indexed: {len(documents):,}")
    print("\nYou can now run the Streamlit app: streamlit run app.py\n")

if __name__ == "__main__":
    main()

