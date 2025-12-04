# Survey RAG App - Enhanced Features

## Overview

This document describes the enhanced features implemented for the Survey RAG application, focusing on improved data ingestion, metadata enrichment, and advanced filtering capabilities for survey analysis.

## 🎯 Enhanced Features

### 1. Metadata Expansion

The ingestion process now creates **comprehensive metadata** for each survey response:

#### Basic Information
- `question`: Separated question text
- `answer`: Separated answer text
- `session_id`: Session identifier
- `topic` / `topic_slug`: Topic categorization

#### Temporal Information
- `date`: Date in YYYY-MM-DD format
- `year_month`: Year-month (YYYY-MM)
- `day_of_week`: Day name (e.g., "Monday")
- `timestamp_unix`: Unix timestamp
- `year`, `month`, `day`, `hour`: Individual time components

#### Quality Metrics
- `response_quality`: Quality label (high/medium/low/very_low)
- `quality_score`: Numerical quality score (0-1)
- `answer_length`: Character count
- `answer_word_count`: Word/character count

#### Sentiment Analysis
- `sentiment_score`: Score from -1 (negative) to +1 (positive)
- `sentiment_label`: Label (positive/slightly_positive/neutral/slightly_negative/negative/unknown)
- `sentiment_positive_words`: Count of positive words
- `sentiment_negative_words`: Count of negative words
- `sentiment_neutral_words`: Count of neutral words

#### Keyword Flags
- `has_positive_keywords`: Boolean flag
- `has_negative_keywords`: Boolean flag
- `has_policy_keywords`: Boolean flag

#### Duplicate Detection
- `is_exact_duplicate`: Boolean flag
- `exact_duplicate_group_id`: Group ID for exact duplicates
- `exact_duplicate_count`: Number of exact duplicates
- `is_fuzzy_duplicate`: Boolean flag
- `fuzzy_duplicate_group_id`: Group ID for similar responses
- `fuzzy_duplicate_count`: Number of similar responses

#### Context Information
- `question_type`: Question classification (open_ended/yes_no/rating/multiple_choice)
- `session_response_order`: Response order within session
- `topic_response_count`: Total responses for this topic

### 2. Enhanced Quality Filtering

Improved response validation with multiple criteria:

- **Minimum length**: 5 characters (Japanese optimized)
- **Meaningless response detection**: Filters out "はい", "いいえ", "わからない", etc.
- **Character variety check**: Ensures meaningful content (not just symbols/numbers)
- **Quality scoring**: Multi-dimensional scoring based on:
  - Length (0-40 points)
  - Sentence count (0-30 points)
  - Character variety (0-30 points)

### 3. Japanese Sentiment Analysis

Dictionary-based sentiment analysis optimized for Japanese text:

#### Sentiment Score Range
- `-1.0`: Very negative
- `0.0`: Neutral
- `+1.0`: Very positive

#### Sentiment Labels
- `positive`: Score ≥ 0.5
- `slightly_positive`: 0.2 ≤ Score < 0.5
- `neutral`: -0.2 ≤ Score < 0.2
- `slightly_negative`: -0.5 ≤ Score < -0.2
- `negative`: Score < -0.5
- `unknown`: No sentiment words detected

#### Sentiment Dictionaries
- **Positive words**: 賛成, 良い, 素晴らしい, 期待, 希望, etc. (20+ words)
- **Negative words**: 反対, 悪い, 問題, 懸念, 不安, etc. (20+ words)
- **Neutral words**: わからない, 不明, どちらとも, etc.

### 4. Duplicate Detection

Identifies and marks duplicate/similar responses:

#### Exact Duplicates
- Uses MD5 hash of normalized text
- Groups identical responses together
- Provides group IDs and counts

#### Fuzzy Duplicates
- Removes punctuation and normalizes whitespace
- Detects near-identical responses
- Useful for finding responses with minor variations

### 5. Advanced Search Filters (Streamlit App)

The enhanced app provides powerful filtering options:

#### Basic Filters
- **Number of results**: 3-20 responses (adjustable slider)
- **Topic filter**: Filter by specific interview topic
- **Date range**: Filter by start/end date

#### Quality Filters
- Select quality levels: high, medium, low, very_low
- Default: high and medium

#### Sentiment Filters
- Select sentiment types: positive, slightly_positive, neutral, slightly_negative, negative, unknown
- Empty selection = no filter

#### Keyword Filters
- Positive opinions only
- Negative opinions only
- Policy-related responses only

#### Duplicate Filters
- Exclude exact duplicates
- Exclude fuzzy duplicates

### 6. Statistics Export

Comprehensive statistics saved to `ingestion_statistics.json`:

```json
{
  "total_documents": 65234,
  "skipped_documents": 1234,
  "ingestion_timestamp": "2025-11-23T12:34:56.789",
  "topic_distribution": {...},
  "quality_distribution": {...},
  "sentiment_distribution": {...},
  "average_sentiment_score": 0.123,
  "duplicate_statistics": {
    "total_exact_duplicate_groups": 123,
    "documents_with_exact_duplicates": 456,
    "total_fuzzy_duplicate_groups": 789,
    "documents_with_fuzzy_duplicates": 1011,
    "unique_responses": 63000
  },
  "date_range": {
    "start": "2025-01-01",
    "end": "2025-11-14"
  },
  "average_answer_length": 123.45,
  "total_sessions": 12345,
  "total_topics": 15
}
```

### 7. Enhanced Statistics Display

The app now shows comprehensive statistics:

#### Main Page Metrics
- Total responses
- Number of sessions
- Number of topics
- Average answer length
- Data date range

#### Sidebar Statistics
- Topic distribution
- Quality distribution
- Sentiment distribution with average score
- Duplicate detection summary

#### Per-Query Statistics
For each query response, displays:
- Number of references used
- Topic distribution
- Quality distribution
- Sentiment analysis (average score + distribution)
- Date range
- Keyword statistics (positive/negative/policy counts)

## 🚀 Usage

### 1. Data Ingestion (Enhanced)

```bash
cd survey_rag_app
python ingest_data.py
```

The enhanced ingestion will:
1. Load and validate all responses
2. Apply quality filtering (minimum 5 chars, meaningful content)
3. Extract temporal information from timestamps
4. Analyze sentiment for each response
5. Detect duplicate and similar responses
6. Generate comprehensive metadata
7. Create vector embeddings
8. Save statistics to `ingestion_statistics.json`

### 2. Running the Enhanced App

```bash
streamlit run app.py
```

Features:
- View overall statistics on the main page
- Configure LLM provider (Ollama or AWS Bedrock)
- Adjust search parameters (number of results)
- Apply advanced filters (topic, date, quality, sentiment, keywords, duplicates)
- View detailed statistics for each response

## 📊 Analysis Capabilities

With the enhanced metadata, you can now:

1. **Temporal Analysis**: Track sentiment trends over time
2. **Topic Analysis**: Compare sentiment across different topics
3. **Quality Assessment**: Identify high-quality vs. low-quality responses
4. **Duplicate Management**: Filter out redundant responses
5. **Sentiment Tracking**: Understand overall sentiment and distribution
6. **Keyword Analysis**: Find specific types of responses (positive/negative/policy)

## 🔧 Configuration

### Quality Filter Settings (ingest_data.py)

```python
MIN_ANSWER_LENGTH = 5  # Minimum characters
MEANINGLESS_ANSWERS = ["はい", "いいえ", "わからない", ...]
```

### Search Settings (app.py)

Default values can be adjusted in the sidebar:
- Number of results: 8 (range: 3-20)
- Quality filter: ["high", "medium"]
- Sentiment filter: [] (all sentiments)

## 📈 Performance Notes

- **Ingestion time**: Slightly increased due to additional processing (sentiment analysis, duplicate detection)
- **Storage**: Metadata size increased by ~30% per document
- **Search performance**: No significant impact; filtering is done post-retrieval
- **Memory usage**: Similar to original implementation

## 🔮 Future Enhancements

Potential improvements:
1. Advanced sentiment analysis using transformers models
2. Entity extraction (names, organizations, locations)
3. Topic modeling and automatic categorization
4. Multi-language support beyond Japanese
5. Real-time sentiment tracking dashboard
6. Response clustering and similarity search
7. Export filtered results to CSV/Excel

## 📝 Notes

- All sentiment analysis is dictionary-based (no external ML models required)
- Duplicate detection uses simple hashing (fast and efficient)
- Temporal parsing handles ISO 8601 format timestamps
- All statistics are recalculated on each ingestion

## 🐛 Troubleshooting

### Issue: Ingestion fails with encoding errors
**Solution**: Ensure JSON file is UTF-8 encoded

### Issue: Sentiment scores seem incorrect
**Solution**: Review and adjust sentiment dictionaries in `analyze_sentiment()` function

### Issue: Too many duplicates detected
**Solution**: Adjust fuzzy matching threshold or use exact duplicate filter only

### Issue: Statistics file not found in app
**Solution**: Run `ingest_data.py` first to generate statistics

## 📚 Related Files

- `ingest_data.py`: Enhanced ingestion with all new features
- `app.py`: Streamlit app with advanced filtering
- `requirements.txt`: No new dependencies added
- `ingestion_statistics.json`: Generated statistics file
- `chroma_db/`: Vector database with enhanced metadata

---

**Version**: 2.0 (Enhanced)  
**Last Updated**: 2025-11-23  
**Compatibility**: Python 3.8+, Streamlit 1.x










