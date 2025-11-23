# Survey RAG Application (Enhanced)

A Retrieval-Augmented Generation (RAG) system for analyzing and querying survey responses using vector search and LLMs.

## 🌟 Features

- **Vector-based search** using ChromaDB and multilingual embeddings
- **Enhanced metadata** with sentiment analysis, quality scoring, and temporal information
- **Duplicate detection** for exact and similar responses
- **Advanced filtering** by topic, date, quality, sentiment, and keywords
- **Flexible LLM support** (Ollama local / AWS Bedrock cloud)
- **Interactive Streamlit interface** with comprehensive statistics
- **Batch summary generation** - Create HTML reports for all survey topics
- **Japanese language optimized** for survey response analysis

## 📊 What's New in Enhanced Version

✨ **Version 2.0** includes major improvements:

- 📈 **Sentiment Analysis**: Dictionary-based Japanese sentiment scoring
- 🎯 **Quality Filtering**: Multi-dimensional quality assessment
- 🔍 **Duplicate Detection**: Identify exact and similar responses
- 📅 **Temporal Analysis**: Full date/time metadata extraction
- 🎨 **Rich Metadata**: 25+ metadata fields per response
- 📊 **Statistics Export**: Comprehensive JSON statistics file
- 🔎 **Advanced Filters**: 10+ filter options in the UI

See [ENHANCED_FEATURES.md](./ENHANCED_FEATURES.md) for detailed documentation.

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Either:
  - Ollama running locally, OR
  - AWS credentials for Bedrock

### Installation

```bash
cd survey_rag_app
pip install -r requirements.txt
```

### Step 1: Data Ingestion

```bash
python ingest_data.py
```

This will:
- Load survey data from JSON backup
- Apply quality filtering and validation
- Perform sentiment analysis
- Detect duplicates
- Create vector embeddings
- Generate statistics file

**Expected output:**
```
SURVEY RAG DATA INGESTION (Enhanced)
==================================================

Loading data from ../backup-2025-11-14T03-19-14.json...
Found 123,456 messages
...
✅ Data ingestion complete!
📁 Vector store saved to ./chroma_db
📊 Total documents indexed: 65,234
📈 Statistics saved to ./ingestion_statistics.json
```

### Step 2: Run the App

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

### Step 3: Generate Survey Summaries (Optional)

Generate comprehensive HTML summaries for each survey topic:

```bash
./generate_summaries.sh
```

Or with custom options:

```bash
# Use AWS Bedrock instead of Ollama
python generate_survey_summaries.py --provider bedrock

# Process specific topics only
python generate_survey_summaries.py --topics marumie-shikin-user mirai-gikai-interview

# Custom output directory
python generate_survey_summaries.py --output-dir ./my_summaries
```

View the generated summaries:

```bash
open survey_summaries_html/index.html
```

See [SUMMARY_GENERATION_GUIDE.md](./SUMMARY_GENERATION_GUIDE.md) for detailed documentation.

## 🎨 User Interface

### Main Page
- Overview statistics (total responses, sessions, topics)
- Date range information
- Quick metrics dashboard

### Sidebar
- **LLM Configuration**
  - Provider selection (Ollama/Bedrock)
  - Model settings
  
- **Search Filters**
  - Number of results (3-20)
  - Topic filter
  - Date range
  - Quality levels
  - Sentiment types
  - Keyword filters
  - Duplicate exclusion

- **Data Statistics**
  - Topic distribution
  - Quality distribution
  - Sentiment analysis
  - Duplicate summary

### Chat Interface
Ask questions about the survey data:
- "国会議員定数削減についてどう思いますか？"
- "ポジティブな意見を教えてください"
- "2025年の回答を見せてください"

## 📁 File Structure

```
survey_rag_app/
├── ingest_data.py                   # Enhanced data ingestion script
├── app.py                           # Streamlit application
├── generate_survey_summaries.py     # Batch summary generator
├── requirements.txt                 # Python dependencies
├── start_app.sh                     # App launcher script
├── ingest.sh                        # Ingestion helper script
├── generate_summaries.sh            # Summary generation script
├── README.md                        # This file
├── QUICKSTART.md                    # Quick start guide
├── ENHANCED_FEATURES.md             # Detailed feature documentation
├── SUMMARY_GENERATION_GUIDE.md      # Summary generation guide
├── chroma_db/                       # Vector database (generated)
├── ingestion_statistics.json        # Statistics file (generated)
└── survey_summaries_html/           # Generated HTML summaries (optional)
    ├── index.html                   # Index page
    └── [topic-slug].html            # Individual topic summaries
```

## 🔧 Configuration

### Ingestion Settings (ingest_data.py)

```python
JSON_FILE_PATH = "../backup-2025-11-14T03-19-14.json"
CHROMA_DB_DIR = "./chroma_db"
EMBEDDING_MODEL = "intfloat/multilingual-e5-base"
MIN_ANSWER_LENGTH = 5
```

### App Settings (app.py)

```python
EMBEDDING_MODEL = "intfloat/multilingual-e5-base"
STATISTICS_FILE = "./ingestion_statistics.json"
```

## 📊 Metadata Fields

Each document includes 25+ metadata fields:

- **Basic**: session_id, topic, question, answer
- **Temporal**: date, year_month, day_of_week, hour
- **Quality**: response_quality, quality_score
- **Sentiment**: sentiment_score, sentiment_label
- **Keywords**: has_positive_keywords, has_negative_keywords, has_policy_keywords
- **Duplicates**: is_exact_duplicate, is_fuzzy_duplicate
- **Context**: question_type, session_response_order

## 🧪 Example Queries

### Basic Query
```
Q: "人工知能についての意見は？"
A: [AI aggregates related responses with statistics]
```

### Filtered Query
1. Enable "詳細フィルタを使用"
2. Select topic: "人工知能基本計画"
3. Select quality: ["high", "medium"]
4. Select sentiment: ["positive", "slightly_positive"]
5. Ask: "どんなメリットが期待されていますか？"

### Temporal Query
1. Enable date filter
2. Set date range: 2025-01-01 to 2025-06-30
3. Ask: "上半期の意見の傾向は？"

## 📈 Statistics

The system tracks comprehensive statistics:

- Total documents and sessions
- Topic distribution (top 10)
- Quality distribution (4 levels)
- Sentiment distribution (6 categories)
- Average sentiment score
- Duplicate statistics
- Date range coverage
- Keyword presence rates

## 🐛 Troubleshooting

### "Vector Database not found"
**Solution**: Run `python ingest_data.py` first

### "Failed to load statistics"
**Solution**: Statistics file is optional; ingestion will create it

### Ollama connection error
**Solution**: 
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama if needed
ollama serve
```

### AWS Bedrock authentication error
**Solution**: 
```bash
# Configure AWS credentials
aws configure

# Or set environment variables
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-east-1
```

## 🔄 Updating Data

To re-ingest data with new survey responses:

```bash
# Backup existing database (optional)
mv chroma_db chroma_db_backup_$(date +%Y%m%d)

# Re-run ingestion
python ingest_data.py
```

The script will ask before overwriting existing data.

## 📚 Dependencies

Main libraries:
- `streamlit`: Web interface
- `langchain`: RAG framework
- `langchain-chroma`: Vector database
- `langchain-huggingface`: Embeddings
- `chromadb`: Vector storage
- `boto3`: AWS Bedrock (optional)
- `sentence-transformers`: Embedding models

No additional dependencies for enhanced features!

## 🚀 Performance

- **Ingestion**: ~2-5 minutes for 65K responses
- **Query time**: 1-3 seconds per query
- **Memory usage**: ~2GB during ingestion, ~500MB during queries
- **Storage**: ~500MB for 65K responses (vector DB + metadata)

## 📝 License

[Add your license here]

## 🤝 Contributing

[Add contributing guidelines here]

## 📧 Contact

[Add contact information here]

---

**Version**: 2.0 (Enhanced)  
**Last Updated**: 2025-11-23  
**Status**: Production Ready

