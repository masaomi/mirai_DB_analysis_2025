#!/bin/bash

# Survey RAG App Startup Script
# Usage: ./start_app.sh

echo "🚀 Starting Survey RAG App..."
echo ""

# Activate conda environment
source /Users/masa/miniconda3/bin/activate mirai_db_analysis_py3.11

# Check if ChromaDB exists
if [ ! -d "./chroma_db" ]; then
    echo "⚠️  ChromaDB not found!"
    echo "Please run: python ingest_data.py first"
    echo ""
    exit 1
fi

echo "✅ Environment: mirai_db_analysis_py3.11"
echo "✅ Python: $(python --version)"
echo "✅ ChromaDB: Found"
echo ""

# Start Streamlit app
echo "Starting Streamlit server..."
echo "Access the app at: http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

streamlit run app.py










