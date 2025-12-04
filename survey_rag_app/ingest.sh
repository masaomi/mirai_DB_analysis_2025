#!/bin/bash

# Survey RAG Data Ingestion Script
# Usage: ./ingest.sh

echo "📊 Starting Survey RAG Data Ingestion..."
echo ""

# Activate conda environment
source /Users/masa/miniconda3/bin/activate mirai_db_analysis_py3.11

echo "✅ Environment: mirai_db_analysis_py3.11"
echo "✅ Python: $(python --version)"
echo ""

# Run ingestion
python ingest_data.py

echo ""
echo "🎉 Ingestion complete!"
echo ""
echo "To start the app, run: ./start_app.sh"









