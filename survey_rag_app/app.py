import streamlit as st
import os
import json
import boto3
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_community.chat_models import ChatOllama
from langchain_aws import ChatBedrock
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from typing import Dict, List, Optional

# Configuration
CHROMA_DB_DIR = "./chroma_db"
COLLECTION_NAME = "survey_responses"
EMBEDDING_MODEL = "intfloat/multilingual-e5-base"  # Multilingual model for better Japanese support
STATISTICS_FILE = "./ingestion_statistics.json"

def load_statistics() -> Optional[Dict]:
    """Load ingestion statistics from JSON file."""
    if os.path.exists(STATISTICS_FILE):
        try:
            with open(STATISTICS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            st.warning(f"Failed to load statistics: {e}")
    return None

def get_embeddings():
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

def get_vectorstore():
    if not os.path.exists(CHROMA_DB_DIR):
        return None
    embeddings = get_embeddings()
    return Chroma(
        persist_directory=CHROMA_DB_DIR,
        embedding_function=embeddings,
        collection_name=COLLECTION_NAME
    )

def init_page():
    st.set_page_config(page_title="仮想回答代表者AI (Enhanced)", layout="wide")
    st.title("💬 仮想回答代表者AI (Enhanced)")
    
    # Load and display statistics
    stats = load_statistics()
    if stats:
        total_docs = stats.get("total_documents", 0)
        date_range = stats.get("date_range", {})
        st.markdown(f"""
        このAIは、**{total_docs:,}件のアンケート回答**を代表する仮想的なスポークスパーソンです。  
        実際の回答データに基づいて、多様な意見や傾向を「私たち」の視点でお答えします。
        
        📅 データ期間: {date_range.get('start', '不明')} 〜 {date_range.get('end', '不明')}
        """)
        
        # Show quick stats in columns
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("総回答数", f"{total_docs:,}")
        with col2:
            st.metric("セッション数", f"{stats.get('total_sessions', 0):,}")
        with col3:
            st.metric("トピック数", f"{stats.get('total_topics', 0):,}")
        with col4:
            avg_len = stats.get('average_answer_length', 0)
            st.metric("平均文字数", f"{avg_len:.0f}")
    else:
        st.markdown("""
        このAIは、アンケート回答を代表する仮想的なスポークスパーソンです。  
        実際の回答データに基づいて、多様な意見や傾向を「私たち」の視点でお答えします。
        """)

def sidebar_config():
    st.sidebar.header("🔧 LLM Configuration")
    
    provider = st.sidebar.selectbox(
        "Select LLM Provider",
        ["Ollama (Local)", "Amazon Bedrock (Cloud)"]
    )
    
    config = {"provider": provider}
    
    if provider == "Ollama (Local)":
        config["base_url"] = st.sidebar.text_input("Base URL", "http://localhost:11434")
        config["model"] = st.sidebar.text_input("Model Name", "gpt-oss:20b")
        st.sidebar.info("Make sure Ollama is running and the model is pulled.")
        
    else: # Bedrock
        config["region"] = st.sidebar.text_input("AWS Region", "us-east-1")
        config["model_id"] = st.sidebar.text_input("Model ID", "anthropic.claude-3-5-sonnet-20240620-v1:0")
        
        # Optional profile selection
        available_profiles = boto3.session.Session().available_profiles
        if available_profiles:
            config["profile"] = st.sidebar.selectbox("AWS Profile", ["default"] + available_profiles)
        else:
            config["profile"] = None
            st.sidebar.warning("No AWS profiles found. Relying on environment variables.")
    
    st.sidebar.markdown("---")
    
    # Search/Filter Configuration
    st.sidebar.header("🔍 Search Filters")
    
    # Load statistics for filter options
    stats = load_statistics()
    
    # Number of results
    config["num_results"] = st.sidebar.slider("検索結果数", min_value=3, max_value=20, value=8, step=1)
    
    # Enable filters
    config["use_filters"] = st.sidebar.checkbox("詳細フィルタを使用", value=False)
    
    if config["use_filters"]:
        config["filters"] = {}
        
        # Topic filter
        if stats and "topic_distribution" in stats:
            topics = ["すべて"] + sorted(stats["topic_distribution"].keys())
            selected_topic = st.sidebar.selectbox("トピックで絞り込み", topics)
            if selected_topic != "すべて":
                config["filters"]["topic"] = selected_topic
        
        # Date range filter
        if stats and "date_range" in stats:
            st.sidebar.subheader("日付範囲")
            use_date_filter = st.sidebar.checkbox("日付で絞り込み", value=False)
            if use_date_filter:
                date_start = st.sidebar.date_input("開始日", value=None)
                date_end = st.sidebar.date_input("終了日", value=None)
                if date_start:
                    config["filters"]["date_start"] = str(date_start)
                if date_end:
                    config["filters"]["date_end"] = str(date_end)
        
        # Quality filter
        st.sidebar.subheader("回答品質")
        quality_options = st.sidebar.multiselect(
            "品質レベル",
            ["high", "medium", "low", "very_low"],
            default=["high", "medium"]
        )
        if quality_options:
            config["filters"]["quality"] = quality_options
        
        # Sentiment filter
        st.sidebar.subheader("感情分析")
        sentiment_options = st.sidebar.multiselect(
            "感情",
            ["positive", "slightly_positive", "neutral", "slightly_negative", "negative", "unknown"],
            default=[]
        )
        if sentiment_options:
            config["filters"]["sentiment"] = sentiment_options
        
        # Keyword filters
        st.sidebar.subheader("キーワード")
        filter_positive = st.sidebar.checkbox("ポジティブな意見のみ", value=False)
        filter_negative = st.sidebar.checkbox("ネガティブな意見のみ", value=False)
        filter_policy = st.sidebar.checkbox("政策関連のみ", value=False)
        
        if filter_positive:
            config["filters"]["has_positive_keywords"] = True
        if filter_negative:
            config["filters"]["has_negative_keywords"] = True
        if filter_policy:
            config["filters"]["has_policy_keywords"] = True
        
        # Duplicate filter
        st.sidebar.subheader("重複除外")
        exclude_exact_duplicates = st.sidebar.checkbox("完全重複を除外", value=False)
        exclude_fuzzy_duplicates = st.sidebar.checkbox("類似重複を除外", value=False)
        
        if exclude_exact_duplicates:
            config["filters"]["exclude_exact_duplicates"] = True
        if exclude_fuzzy_duplicates:
            config["filters"]["exclude_fuzzy_duplicates"] = True
    
    st.sidebar.markdown("---")
    
    # Show statistics in expander
    if stats:
        with st.sidebar.expander("📊 データ統計情報"):
            st.write(f"**総ドキュメント数**: {stats.get('total_documents', 0):,}")
            st.write(f"**セッション数**: {stats.get('total_sessions', 0):,}")
            st.write(f"**トピック数**: {stats.get('total_topics', 0):,}")
            
            if "quality_distribution" in stats:
                st.write("**品質分布**:")
                for quality, count in stats["quality_distribution"].items():
                    st.write(f"  - {quality}: {count:,}")
            
            if "sentiment_distribution" in stats:
                st.write("**感情分布**:")
                avg_sentiment = stats.get("average_sentiment_score", 0)
                st.write(f"  - 平均スコア: {avg_sentiment:.3f}")
                for sentiment, count in stats["sentiment_distribution"].items():
                    st.write(f"  - {sentiment}: {count:,}")
            
            if "duplicate_statistics" in stats:
                dup_stats = stats["duplicate_statistics"]
                st.write("**重複検出**:")
                st.write(f"  - ユニーク回答: {dup_stats.get('unique_responses', 0):,}")
                st.write(f"  - 完全重複: {dup_stats.get('documents_with_exact_duplicates', 0):,}")
                st.write(f"  - 類似重複: {dup_stats.get('documents_with_fuzzy_duplicates', 0):,}")
            
    return config

def get_llm(config):
    if config["provider"] == "Ollama (Local)":
        return ChatOllama(
            base_url=config["base_url"],
            model=config["model"],
            temperature=0.3
        )
    else: # Bedrock
        try:
            # Setup boto3 session
            if config.get("profile"):
                session = boto3.Session(profile_name=config["profile"], region_name=config["region"])
                client = session.client("bedrock-runtime")
            else:
                client = boto3.client("bedrock-runtime", region_name=config["region"])
                
            return ChatBedrock(
                client=client,
                model_id=config["model_id"],
                model_kwargs={"temperature": 0.3, "max_tokens": 1000}
            )
        except Exception as e:
            st.error(f"Error initializing Bedrock: {e}")
            return None

def apply_metadata_filters(docs: List, filters: Dict) -> List:
    """Apply metadata filters to retrieved documents."""
    if not filters:
        return docs
    
    filtered_docs = []
    for doc in docs:
        # Check all filter conditions
        passes = True
        
        # Topic filter
        if "topic" in filters:
            if doc.metadata.get("topic") != filters["topic"]:
                passes = False
        
        # Date range filters
        if "date_start" in filters:
            if doc.metadata.get("date", "") < filters["date_start"]:
                passes = False
        if "date_end" in filters:
            if doc.metadata.get("date", "") > filters["date_end"]:
                passes = False
        
        # Quality filter
        if "quality" in filters:
            if doc.metadata.get("response_quality") not in filters["quality"]:
                passes = False
        
        # Sentiment filter
        if "sentiment" in filters:
            if doc.metadata.get("sentiment_label") not in filters["sentiment"]:
                passes = False
        
        # Keyword filters
        if "has_positive_keywords" in filters:
            if not doc.metadata.get("has_positive_keywords", False):
                passes = False
        if "has_negative_keywords" in filters:
            if not doc.metadata.get("has_negative_keywords", False):
                passes = False
        if "has_policy_keywords" in filters:
            if not doc.metadata.get("has_policy_keywords", False):
                passes = False
        
        # Duplicate filters
        if filters.get("exclude_exact_duplicates", False):
            if doc.metadata.get("is_exact_duplicate", False):
                passes = False
        if filters.get("exclude_fuzzy_duplicates", False):
            if doc.metadata.get("is_fuzzy_duplicate", False):
                passes = False
        
        if passes:
            filtered_docs.append(doc)
    
    return filtered_docs

def format_docs(docs):
    """Format documents with enhanced metadata for better context"""
    formatted = []
    for i, doc in enumerate(docs, 1):
        topic = doc.metadata.get('topic', '不明')
        question = doc.metadata.get('question', '不明')
        answer = doc.metadata.get('answer', doc.page_content)
        date = doc.metadata.get('date', '不明')
        quality = doc.metadata.get('response_quality', '不明')
        
        formatted.append(
            f"【回答例{i}】\n"
            f"トピック: {topic}\n"
            f"日付: {date}\n"
            f"質問: {question}\n"
            f"回答: {answer}\n"
            f"品質: {quality}"
        )
    return "\n\n".join(formatted)

def get_response_stats(docs):
    """Get enhanced statistics about retrieved documents"""
    from collections import Counter
    
    topics = [doc.metadata.get('topic', '不明') for doc in docs]
    topic_counts = Counter(topics)
    
    qualities = [doc.metadata.get('response_quality', '不明') for doc in docs]
    quality_counts = Counter(qualities)
    
    sentiments = [doc.metadata.get('sentiment_label', '不明') for doc in docs]
    sentiment_counts = Counter(sentiments)
    
    # Calculate average sentiment score
    sentiment_scores = [doc.metadata.get('sentiment_score', 0) for doc in docs]
    avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
    
    dates = [doc.metadata.get('date', '不明') for doc in docs]
    date_range = {
        'start': min(dates) if dates else '不明',
        'end': max(dates) if dates else '不明'
    }
    
    # Count keyword presence
    positive_count = sum(1 for doc in docs if doc.metadata.get('has_positive_keywords', False))
    negative_count = sum(1 for doc in docs if doc.metadata.get('has_negative_keywords', False))
    policy_count = sum(1 for doc in docs if doc.metadata.get('has_policy_keywords', False))
    
    return {
        'total': len(docs),
        'topics': dict(topic_counts),
        'qualities': dict(quality_counts),
        'sentiments': dict(sentiment_counts),
        'average_sentiment': round(avg_sentiment, 3),
        'date_range': date_range,
        'keyword_stats': {
            'positive': positive_count,
            'negative': negative_count,
            'policy': policy_count
        }
    }

def main():
    init_page()
    config = sidebar_config()
    
    # Check for Vector Store
    vectorstore = get_vectorstore()
    if not vectorstore:
        st.error(f"Vector Database not found at {CHROMA_DB_DIR}. Please run `ingest_data.py` first.")
        return

    # Initialize Session State
    if "messages" not in st.session_state:
        st.session_state.messages = []
        
    # Display Chat History
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat Input
    if prompt := st.chat_input("アンケート回答者に何を聞きたいですか？（例：国会議員定数削減についてどう思いますか？）"):
        # Add user message to state
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate Response
        with st.chat_message("assistant"):
            llm = get_llm(config)
            if not llm:
                st.stop()
            
            # Get number of results from config
            num_results = config.get("num_results", 8)
            retriever = vectorstore.as_retriever(search_kwargs={"k": num_results})
            
            # Retrieve relevant documents
            retrieved_docs = retriever.invoke(prompt)
            
            # Apply metadata filters if enabled
            if config.get("use_filters") and config.get("filters"):
                original_count = len(retrieved_docs)
                retrieved_docs = apply_metadata_filters(retrieved_docs, config["filters"])
                filtered_count = len(retrieved_docs)
                
                if filtered_count < original_count:
                    st.info(f"フィルタ適用: {original_count}件 → {filtered_count}件に絞り込みました")
                
                if filtered_count == 0:
                    st.warning("フィルタ条件に一致する回答が見つかりませんでした。フィルタを緩めてください。")
                    st.stop()
            
            stats = get_response_stats(retrieved_docs)
            context = format_docs(retrieved_docs)
            
            # Enhanced prompt for virtual representative persona
            template = """あなたは、各種アンケート調査に回答した65,234人の意見を代表する仮想的なスポークスパーソンです。

【あなたの役割】
- 実際のアンケート回答データに基づいて回答する
- 多数派の意見だけでなく、多様な視点や少数意見も考慮する
- 「私たち回答者は」という視点で語る
- データにない情報については推測せず、正直に「データにはありません」と答える

【参考にする実際の回答】
以下は、あなたの質問に関連する実際のアンケート回答です：

{context}

【統計情報】
- 参照した回答数: {num_responses}件
- 関連トピック: {topics}

【質問】
{question}

【回答】
上記の実際の回答を踏まえ、回答者を代表する立場として、以下のように答えます："""
            
            prompt_template = PromptTemplate.from_template(
                template,
                partial_variables={
                    "num_responses": str(stats['total']),
                    "topics": ", ".join(stats['topics'].keys())
                }
            )
            
            rag_chain = (
                {"context": lambda x: context, "question": RunnablePassthrough()}
                | prompt_template
                | llm
                | StrOutputParser()
            )
            
            with st.spinner("回答者の意見を集約しています..."):
                try:
                    result = rag_chain.invoke(prompt)
                    
                    # Display the answer
                    st.markdown(result)
                    
                    # Show enhanced statistics in an expander
                    with st.expander("📊 参照した回答の詳細"):
                        st.write(f"**参照回答数**: {stats['total']}件")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write("**トピック分布**:")
                            for topic, count in stats['topics'].items():
                                st.write(f"- {topic}: {count}件")
                            
                            st.write("**品質分布**:")
                            for quality, count in stats['qualities'].items():
                                st.write(f"- {quality}: {count}件")
                            
                            st.write("**感情分析**:")
                            st.write(f"- 平均スコア: {stats['average_sentiment']:.3f}")
                            for sentiment, count in stats['sentiments'].items():
                                st.write(f"- {sentiment}: {count}件")
                        
                        with col2:
                            st.write("**日付範囲**:")
                            st.write(f"- 開始: {stats['date_range']['start']}")
                            st.write(f"- 終了: {stats['date_range']['end']}")
                            
                            st.write("**キーワード統計**:")
                            st.write(f"- ポジティブ: {stats['keyword_stats']['positive']}件")
                            st.write(f"- ネガティブ: {stats['keyword_stats']['negative']}件")
                            st.write(f"- 政策関連: {stats['keyword_stats']['policy']}件")
                    
                    st.session_state.messages.append({"role": "assistant", "content": result})
                except Exception as e:
                    st.error(f"An error occurred: {e}")
                    import traceback
                    st.code(traceback.format_exc())

if __name__ == "__main__":
    main()
