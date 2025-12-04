#!/usr/bin/env python3
"""
回答のカテゴリ化・クラスタリングスクリプト

自由記述式の回答をカテゴリ化し、分析しやすくします
"""

import json
import re
from collections import Counter, defaultdict
from typing import Dict, List, Any, Tuple
import sys

# Try to import NLP libraries
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.cluster import KMeans
    from sklearn.decomposition import LatentDirichletAllocation
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    print("Warning: scikit-learn not installed. Advanced clustering will be skipped.")

try:
    import MeCab
    HAS_MECAB = True
except ImportError:
    HAS_MECAB = False
    print("Warning: MeCab not installed. Japanese text analysis may be limited.")


class ResponseCategorizer:
    def __init__(self, json_file_path: str):
        """Initialize categorizer"""
        print(f"Loading data from {json_file_path}...")
        with open(json_file_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        self.tables = self.data['tables']
        print("Data loaded successfully!")
        
    def extract_responses_by_topic(self, topic_slug: str) -> List[Dict[str, Any]]:
        """Extract all user responses for a specific topic"""
        sessions = self.tables['interview_sessions']
        messages = self.tables['messages']
        
        topic_sessions = [s for s in sessions if s.get('slug') == topic_slug]
        session_ids = {s['id'] for s in topic_sessions}
        
        responses = []
        for m in messages:
            if m.get('session_id') in session_ids and m.get('role') == 'user':
                content = m.get('content', '').strip()
                if content and len(content) > 5:  # Filter very short responses
                    responses.append({
                        'content': content,
                        'session_id': m.get('session_id'),
                        'timestamp': m.get('timestamp'),
                        'length': len(content)
                    })
        
        return responses
    
    def categorize_by_length(self, responses: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Categorize responses by length"""
        categories = {
            'very_short': [],  # 0-30 chars
            'short': [],       # 31-100 chars
            'medium': [],      # 101-300 chars
            'long': [],        # 301-1000 chars
            'very_long': []    # 1000+ chars
        }
        
        for resp in responses:
            length = resp['length']
            if length <= 30:
                categories['very_short'].append(resp)
            elif length <= 100:
                categories['short'].append(resp)
            elif length <= 300:
                categories['medium'].append(resp)
            elif length <= 1000:
                categories['long'].append(resp)
            else:
                categories['very_long'].append(resp)
        
        return categories
    
    def extract_sentiment_keywords(self, text: str) -> Dict[str, int]:
        """Simple sentiment keyword extraction"""
        # Positive keywords
        positive_keywords = ['良い', 'いい', '賛成', '支持', '期待', '有用', '効果的', 
                           'good', 'great', 'excellent', 'positive', 'support', 'agree']
        
        # Negative keywords
        negative_keywords = ['悪い', '問題', '懸念', '反対', '不安', 'リスク', '課題',
                           'bad', 'problem', 'concern', 'risk', 'issue', 'worry', 'disagree']
        
        # Question keywords
        question_keywords = ['？', '?', 'どう', 'なぜ', '何', 'どの', 'why', 'what', 'how', 'when']
        
        text_lower = text.lower()
        
        return {
            'positive': sum(1 for kw in positive_keywords if kw.lower() in text_lower),
            'negative': sum(1 for kw in negative_keywords if kw.lower() in text_lower),
            'question': sum(1 for kw in question_keywords if kw in text)
        }
    
    def categorize_by_sentiment(self, responses: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Categorize responses by sentiment keywords"""
        categories = {
            'positive': [],
            'negative': [],
            'neutral': [],
            'question': []
        }
        
        for resp in responses:
            content = resp['content']
            sentiment = self.extract_sentiment_keywords(content)
            
            if sentiment['question'] > 0:
                categories['question'].append(resp)
            elif sentiment['positive'] > sentiment['negative']:
                categories['positive'].append(resp)
            elif sentiment['negative'] > sentiment['positive']:
                categories['negative'].append(resp)
            else:
                categories['neutral'].append(resp)
        
        return categories
    
    def extract_key_phrases(self, responses: List[Dict[str, Any]], top_n: int = 20) -> List[Tuple[str, int]]:
        """Extract key phrases from responses"""
        # Simple n-gram extraction (can be enhanced)
        all_phrases = []
        
        for resp in responses:
            content = resp['content']
            # Extract 2-3 word phrases
            words = re.findall(r'\w+', content.lower())
            for i in range(len(words) - 1):
                phrase = f"{words[i]} {words[i+1]}"
                all_phrases.append(phrase)
            for i in range(len(words) - 2):
                phrase = f"{words[i]} {words[i+1]} {words[i+2]}"
                all_phrases.append(phrase)
        
        phrase_counts = Counter(all_phrases)
        return phrase_counts.most_common(top_n)
    
    def cluster_responses(self, responses: List[Dict[str, Any]], n_clusters: int = 5) -> Dict[int, List[Dict[str, Any]]]:
        """Cluster responses using K-means (requires sklearn)"""
        if not HAS_SKLEARN:
            print("Skipping clustering: scikit-learn not installed")
            return {}
        
        if len(responses) < n_clusters:
            print(f"Not enough responses for clustering (need at least {n_clusters})")
            return {}
        
        # Prepare text data
        texts = [r['content'] for r in responses]
        
        # Vectorize
        vectorizer = TfidfVectorizer(max_features=100, stop_words='english', 
                                   min_df=2, max_df=0.95)
        try:
            X = vectorizer.fit_transform(texts)
            
            # Cluster
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            clusters = kmeans.fit_predict(X)
            
            # Group responses by cluster
            clustered = defaultdict(list)
            for resp, cluster_id in zip(responses, clusters):
                clustered[int(cluster_id)].append(resp)
            
            return dict(clustered)
        except Exception as e:
            print(f"Clustering failed: {e}")
            return {}
    
    def analyze_topic(self, topic_slug: str) -> Dict[str, Any]:
        """Comprehensive analysis of a topic"""
        print(f"\nAnalyzing topic: {topic_slug}")
        print("-" * 80)
        
        responses = self.extract_responses_by_topic(topic_slug)
        
        if not responses:
            print(f"No responses found for topic: {topic_slug}")
            return {}
        
        print(f"Total responses: {len(responses)}")
        
        # Length categorization
        length_cats = self.categorize_by_length(responses)
        print("\nLength distribution:")
        for cat, items in length_cats.items():
            print(f"  {cat}: {len(items)} ({len(items)/len(responses)*100:.1f}%)")
        
        # Sentiment categorization
        sentiment_cats = self.categorize_by_sentiment(responses)
        print("\nSentiment distribution:")
        for cat, items in sentiment_cats.items():
            print(f"  {cat}: {len(items)} ({len(items)/len(responses)*100:.1f}%)")
        
        # Key phrases
        key_phrases = self.extract_key_phrases(responses)
        print("\nTop key phrases:")
        for phrase, count in key_phrases[:10]:
            print(f"  '{phrase}': {count} times")
        
        # Clustering (if available)
        if HAS_SKLEARN and len(responses) >= 5:
            print("\nClustering responses...")
            clusters = self.cluster_responses(responses, n_clusters=min(5, len(responses)//10))
            if clusters:
                print(f"Found {len(clusters)} clusters:")
                for cluster_id, cluster_responses in clusters.items():
                    print(f"  Cluster {cluster_id}: {len(cluster_responses)} responses")
                    # Show sample from cluster
                    if cluster_responses:
                        sample = cluster_responses[0]['content'][:100]
                        print(f"    Sample: {sample}...")
        
        return {
            'topic': topic_slug,
            'total_responses': len(responses),
            'length_categories': {k: len(v) for k, v in length_cats.items()},
            'sentiment_categories': {k: len(v) for k, v in sentiment_cats.items()},
            'key_phrases': key_phrases[:20],
            'sample_responses': [r['content'][:200] for r in responses[:5]]
        }
    
    def generate_categorization_report(self, topic_slugs: List[str] = None) -> str:
        """Generate categorization report for specified topics"""
        if topic_slugs is None:
            # Analyze top topics by default
            sessions = self.tables['interview_sessions']
            topic_counts = Counter(s.get('slug') for s in sessions if s.get('slug'))
            topic_slugs = [slug for slug, _ in topic_counts.most_common(5)]
        
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("回答カテゴリ化レポート")
        report_lines.append("=" * 80)
        report_lines.append("")
        
        all_analyses = []
        for slug in topic_slugs:
            analysis = self.analyze_topic(slug)
            if analysis:
                all_analyses.append(analysis)
        
        # Summary
        report_lines.append("## サマリー")
        report_lines.append("-" * 80)
        for analysis in all_analyses:
            report_lines.append(f"\n### {analysis['topic']}")
            report_lines.append(f"総回答数: {analysis['total_responses']}")
            report_lines.append(f"長さ分布: {analysis['length_categories']}")
            report_lines.append(f"感情分布: {analysis['sentiment_categories']}")
        
        return "\n".join(report_lines)


def main():
    json_file = "backup-2025-11-14T03-19-14.json"
    
    categorizer = ResponseCategorizer(json_file)
    
    # Analyze top topics
    sessions = categorizer.tables['interview_sessions']
    topic_counts = Counter(s.get('slug') for s in sessions if s.get('slug'))
    top_topics = [slug for slug, _ in topic_counts.most_common(3)]
    
    print("\n" + "=" * 80)
    print("Analyzing top topics:")
    print("=" * 80)
    
    for topic in top_topics:
        categorizer.analyze_topic(topic)
        print()


if __name__ == "__main__":
    main()


