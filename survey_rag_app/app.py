import streamlit as st
import os
import boto3
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_community.chat_models import ChatOllama
from langchain_aws import ChatBedrock
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

# Configuration
CHROMA_DB_DIR = "./chroma_db"
COLLECTION_NAME = "survey_responses"
EMBEDDING_MODEL = "intfloat/multilingual-e5-base"  # Multilingual model for better Japanese support

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
    st.set_page_config(page_title="仮想回答代表者AI", layout="wide")
    st.title("💬 仮想回答代表者AI")
    st.markdown("""
    このAIは、**65,234件のアンケート回答**を代表する仮想的なスポークスパーソンです。  
    実際の回答データに基づいて、多様な意見や傾向を「私たち」の視点でお答えします。
    """)

def sidebar_config():
    st.sidebar.header("LLM Configuration")
    
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

def format_docs(docs):
    """Format documents with metadata for better context"""
    formatted = []
    for i, doc in enumerate(docs, 1):
        topic = doc.metadata.get('topic', '不明')
        content = doc.page_content
        formatted.append(f"【回答例{i}】（トピック: {topic}）\n{content}")
    return "\n\n".join(formatted)

def get_response_stats(docs):
    """Get statistics about retrieved documents"""
    topics = [doc.metadata.get('topic', '不明') for doc in docs]
    from collections import Counter
    topic_counts = Counter(topics)
    return {
        'total': len(docs),
        'topics': dict(topic_counts)
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
                
            retriever = vectorstore.as_retriever(search_kwargs={"k": 8})
            
            # Retrieve relevant documents
            retrieved_docs = retriever.invoke(prompt)
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
                    
                    # Show statistics in an expander
                    with st.expander("📊 参照した回答の詳細"):
                        st.write(f"**参照回答数**: {stats['total']}件")
                        st.write("**トピック分布**:")
                        for topic, count in stats['topics'].items():
                            st.write(f"- {topic}: {count}件")
                    
                    st.session_state.messages.append({"role": "assistant", "content": result})
                except Exception as e:
                    st.error(f"An error occurred: {e}")
                    import traceback
                    st.code(traceback.format_exc())

if __name__ == "__main__":
    main()
