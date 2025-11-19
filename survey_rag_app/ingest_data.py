import json
import os
from typing import List, Dict
from datetime import datetime
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

# Configuration
JSON_FILE_PATH = "../backup-2025-11-14T03-19-14.json"
CHROMA_DB_DIR = "./chroma_db"
COLLECTION_NAME = "survey_responses"

def load_and_process_data(file_path: str) -> List[Document]:
    """
    Load JSON data and extract user responses with context.
    """
    print(f"Loading data from {file_path}...")
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    messages = data.get("tables", {}).get("messages", [])
    if not messages:
        # Fallback if structure is different
        messages = data.get("messages", [])
        
    print(f"Found {len(messages)} messages. Processing...")

    # Group messages by session_id
    sessions: Dict[str, List[Dict]] = {}
    for msg in messages:
        session_id = msg.get("session_id")
        if not session_id:
            continue
        if session_id not in sessions:
            sessions[session_id] = []
        sessions[session_id].append(msg)

    documents = []
    
    # Process each session
    for session_id, session_msgs in sessions.items():
        # Sort messages by timestamp
        session_msgs.sort(key=lambda x: x.get("timestamp", ""))
        
        for i in range(len(session_msgs)):
            msg = session_msgs[i]
            
            # We are interested in USER messages
            if msg.get("role") == "user":
                user_content = msg.get("content", "").strip()
                
                # Skip empty or very short responses
                if not user_content or len(user_content) < 2:
                    continue
                
                # Find the preceding assistant message (Question)
                question = "Unknown Question"
                if i > 0 and session_msgs[i-1].get("role") == "assistant":
                    question = session_msgs[i-1].get("content", "").strip()
                
                # Create document content
                # We format it as Q&A pair to give context to the embedding
                page_content = f"Question: {question}\nAnswer: {user_content}"
                
                metadata = {
                    "session_id": session_id,
                    "timestamp": msg.get("timestamp"),
                    "role": "user",
                    "type": "survey_response"
                }
                
                documents.append(Document(page_content=page_content, metadata=metadata))

    print(f"Created {len(documents)} documents from survey responses.")
    return documents

def main():
    # 1. Load Documents
    try:
        documents = load_and_process_data(JSON_FILE_PATH)
    except Exception as e:
        print(f"Error loading data: {e}")
        return

    if not documents:
        print("No documents to ingest.")
        return

    # 2. Initialize Embeddings
    print("Initializing Embeddings (HuggingFace all-MiniLM-L6-v2)...")
    # Using a standard lightweight model good for Japanese/English mix usually works okay, 
    # but for better Japanese support "intfloat/multilingual-e5-large" is better.
    # However, sticking to the plan's suggestion or a standard one for speed.
    # The plan mentioned 'all-MiniLM-L6-v2'.
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    # 3. Create/Update Vector Store
    print(f"Creating Vector Store in {CHROMA_DB_DIR}...")
    
    # Check if directory exists, clean it if you want a fresh start or just append
    # For this task, we'll persist.
    
    vector_store = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=CHROMA_DB_DIR,
        collection_name=COLLECTION_NAME
    )
    
    print("Data ingestion complete!")
    print(f"Vector store saved to {CHROMA_DB_DIR}")

if __name__ == "__main__":
    main()

