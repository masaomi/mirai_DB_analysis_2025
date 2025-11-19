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

def get_embeddings():
    return HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

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
    st.set_page_config(page_title="Survey RAG Chat", layout="wide")
    st.title("📊 Survey Data RAG Chat")
    st.markdown("Ask questions based on the survey responses database.")

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
    return "\n\n".join(doc.page_content for doc in docs)

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
    if prompt := st.chat_input("What would you like to know about the survey results?"):
        # Add user message to state
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate Response
        with st.chat_message("assistant"):
            llm = get_llm(config)
            if not llm:
                st.stop()
                
            retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
            
            # Create a simple RAG chain
            template = """Answer the question based only on the following context:
{context}

Question: {question}

Answer: """
            
            prompt_template = PromptTemplate.from_template(template)
            
            rag_chain = (
                {"context": retriever | format_docs, "question": RunnablePassthrough()}
                | prompt_template
                | llm
                | StrOutputParser()
            )
            
            with st.spinner("Thinking..."):
                try:
                    result = rag_chain.invoke(prompt)
                    st.markdown(result)
                    st.session_state.messages.append({"role": "assistant", "content": result})
                except Exception as e:
                    st.error(f"An error occurred: {e}")
                    import traceback
                    st.code(traceback.format_exc())

if __name__ == "__main__":
    main()
