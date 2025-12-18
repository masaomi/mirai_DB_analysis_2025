#!/bin/bash

# Survey Summary Generation Script
# Usage: ./generate_summaries.sh [options]

echo "📊 Survey Summary Generator"
echo "================================"
echo ""

# Activate conda environment
source /Users/masa/miniconda3/bin/activate mirai_db_analysis_py3.11

echo "✅ Environment: mirai_db_analysis_py3.11"
echo "✅ Python: $(python --version)"
echo ""

# Check if ChromaDB exists
if [ ! -d "./chroma_db" ]; then
    echo "❌ ChromaDB not found!"
    echo "Please run: ./ingest.sh first"
    echo ""
    exit 1
fi

echo "✅ ChromaDB: Found"
echo ""

# Default: Use Ollama with gpt-oss:20b
echo "🤖 LLM Provider: Ollama (Local)"
echo "📝 Model: gpt-oss:20b"
echo ""

echo "Starting summary generation..."
echo ""

# Run the generator
python generate_survey_summaries.py "$@"

echo ""
echo "✨ Summary generation complete!"
echo ""
echo "To view results:"
echo "  open survey_summaries_html/index.html"
echo ""

















