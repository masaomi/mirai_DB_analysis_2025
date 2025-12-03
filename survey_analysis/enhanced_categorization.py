#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Categorization Module
TF-IDF + クラスタリングによる高度なカテゴリ化
"""

import MeCab
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')


class JapaneseTfidfVectorizer:
    """
    Japanese text vectorizer using MeCab for tokenization
    """
    
    def __init__(self):
        try:
            self.mecab = MeCab.Tagger()
        except Exception as e:
            print(f"Warning: MeCab initialization failed: {e}")
            print("Falling back to character-based tokenization")
            self.mecab = None
        
        # Part of speech to keep (名詞、動詞、形容詞)
        self.pos_to_keep = ['名詞', '動詞', '形容詞']
        
        # Stop words (common words to exclude)
        self.stop_words = {
            'こと', 'もの', 'ため', 'よう', 'そう', 'ところ', 'の', 'は', 'が', 'を',
            'に', 'へ', 'と', 'で', 'や', 'から', 'より', 'まで', 'て', 'で',
            'する', 'なる', 'ある', 'いる', 'できる', 'いう', 'れる', 'られる',
            'です', 'ます', 'ません', 'でした', 'だ', 'な', 'ない', 'た',
        }
    
    def tokenize(self, text: str) -> List[str]:
        """
        Tokenize Japanese text using MeCab
        
        Args:
            text: Input text
            
        Returns:
            List of tokens (words)
        """
        if self.mecab is None:
            # Fallback: simple character-based tokenization
            return [char for char in text if char.strip()]
        
        try:
            node = self.mecab.parseToNode(text)
            tokens = []
            
            while node:
                features = node.feature.split(',')
                pos = features[0]  # Part of speech
                surface = node.surface
                
                # Keep only relevant POS and filter stop words
                if pos in self.pos_to_keep and len(surface) > 1:
                    base_form = features[6] if len(features) > 6 else surface
                    if base_form not in self.stop_words and base_form != '*':
                        tokens.append(base_form)
                
                node = node.next
            
            return tokens
        except Exception as e:
            print(f"Warning: Tokenization failed: {e}")
            return []
    
    def tokenize_batch(self, texts: List[str]) -> List[str]:
        """
        Tokenize multiple texts
        
        Args:
            texts: List of texts
            
        Returns:
            List of tokenized texts (space-separated)
        """
        return [' '.join(self.tokenize(text)) for text in texts]


class EnhancedCategorizer:
    """
    Enhanced categorization using TF-IDF and clustering
    """
    
    def __init__(self, min_cluster_size: int = 3):
        self.tokenizer = JapaneseTfidfVectorizer()
        self.vectorizer = None
        self.min_cluster_size = min_cluster_size
    
    def find_optimal_clusters(self, vectors: np.ndarray, max_k: int = 10) -> int:
        """
        Find optimal number of clusters using elbow method and silhouette score
        
        Args:
            vectors: TF-IDF vectors
            max_k: Maximum number of clusters to try
            
        Returns:
            Optimal number of clusters
        """
        n_samples = vectors.shape[0]
        
        # Limit max_k based on number of samples
        max_k = min(max_k, max(2, n_samples // self.min_cluster_size))
        
        if max_k < 2:
            return 2
        
        silhouette_scores = []
        K_range = range(2, max_k + 1)
        
        for k in K_range:
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            labels = kmeans.fit_predict(vectors)
            score = silhouette_score(vectors, labels)
            silhouette_scores.append(score)
        
        # Return k with highest silhouette score
        optimal_k = K_range[np.argmax(silhouette_scores)]
        
        return optimal_k
    
    def extract_top_keywords(self, responses: List[Dict], n_keywords: int = 20) -> List[Tuple[str, float]]:
        """
        Extract top keywords using TF-IDF
        
        Args:
            responses: List of response dictionaries
            n_keywords: Number of top keywords to extract
            
        Returns:
            List of (keyword, score) tuples
        """
        texts = [resp.get('content', '') for resp in responses]
        
        # Tokenize texts
        tokenized_texts = self.tokenizer.tokenize_batch(texts)
        
        # Apply TF-IDF
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            min_df=2,  # Minimum document frequency
            max_df=0.8,  # Maximum document frequency (exclude too common words)
        )
        
        try:
            tfidf_matrix = self.vectorizer.fit_transform(tokenized_texts)
        except ValueError as e:
            print(f"Warning: TF-IDF failed: {e}")
            return []
        
        # Get feature names (words)
        feature_names = self.vectorizer.get_feature_names_out()
        
        # Calculate average TF-IDF score for each word
        avg_scores = np.asarray(tfidf_matrix.mean(axis=0)).flatten()
        
        # Get top keywords
        top_indices = avg_scores.argsort()[-n_keywords:][::-1]
        top_keywords = [(feature_names[i], avg_scores[i]) for i in top_indices]
        
        return top_keywords
    
    def categorize_by_clustering(
        self, 
        responses: List[Dict], 
        n_clusters: Optional[int] = None
    ) -> Dict[str, List[Dict]]:
        """
        Categorize responses using K-means clustering
        
        Args:
            responses: List of response dictionaries
            n_clusters: Number of clusters (if None, will be determined automatically)
            
        Returns:
            Dictionary mapping cluster labels to responses
        """
        if len(responses) < 2:
            return {'すべての回答': responses}
        
        texts = [resp.get('content', '') for resp in responses]
        
        # Tokenize texts
        tokenized_texts = self.tokenizer.tokenize_batch(texts)
        
        # Apply TF-IDF
        self.vectorizer = TfidfVectorizer(
            max_features=500,
            min_df=1,
            max_df=0.9,
        )
        
        try:
            tfidf_matrix = self.vectorizer.fit_transform(tokenized_texts)
        except ValueError as e:
            print(f"Warning: TF-IDF failed: {e}. Using single category.")
            return {'すべての回答': responses}
        
        # Determine optimal number of clusters
        if n_clusters is None:
            n_clusters = self.find_optimal_clusters(tfidf_matrix)
        
        # Perform clustering
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(tfidf_matrix)
        
        # Get top keywords for each cluster
        feature_names = self.vectorizer.get_feature_names_out()
        cluster_keywords = {}
        
        for cluster_id in range(n_clusters):
            # Get center of this cluster
            center = kmeans.cluster_centers_[cluster_id]
            
            # Get top keywords for this cluster
            top_indices = center.argsort()[-5:][::-1]
            keywords = [feature_names[i] for i in top_indices if center[i] > 0]
            
            cluster_keywords[cluster_id] = keywords
        
        # Group responses by cluster
        categorized = defaultdict(list)
        
        for i, (response, label) in enumerate(zip(responses, cluster_labels)):
            # Create cluster name from top keywords
            keywords = cluster_keywords[label]
            if keywords:
                cluster_name = '・'.join(keywords[:3])
            else:
                cluster_name = f'カテゴリ{label + 1}'
            
            # Add cluster info to response
            response_with_cluster = response.copy()
            response_with_cluster['cluster_id'] = int(label)
            response_with_cluster['cluster_keywords'] = keywords
            
            categorized[cluster_name].append(response_with_cluster)
        
        return dict(categorized)
    
    def hybrid_categorization(
        self,
        responses: List[Dict],
        use_intent: bool = True,
        use_clustering: bool = True
    ) -> Dict[str, List[Dict]]:
        """
        Hybrid categorization combining intent-based and clustering-based approaches
        
        Args:
            responses: List of response dictionaries
            use_intent: Whether to use intent-based categorization
            use_clustering: Whether to use clustering
            
        Returns:
            Dictionary mapping category names to responses
        """
        if len(responses) < self.min_cluster_size:
            return {'すべての回答': responses}
        
        # First, try clustering
        if use_clustering:
            categories = self.categorize_by_clustering(responses)
            
            # If "その他" or uncategorized is too large, try to split it
            for category_name, category_responses in list(categories.items()):
                if len(category_responses) > len(responses) * 0.4:  # More than 40%
                    # Try to sub-cluster
                    if len(category_responses) >= self.min_cluster_size * 2:
                        sub_categories = self.categorize_by_clustering(
                            category_responses,
                            n_clusters=min(3, len(category_responses) // self.min_cluster_size)
                        )
                        
                        # Replace the large category with sub-categories
                        del categories[category_name]
                        for sub_name, sub_responses in sub_categories.items():
                            categories[f"{category_name}_{sub_name}"] = sub_responses
            
            return categories
        else:
            return {'すべての回答': responses}


def test_enhanced_categorization():
    """Test function for enhanced categorization"""
    # Create sample data
    sample_responses = [
        {'content': '政治の透明性を高めることが重要です', 'session_id': 1},
        {'content': '政治資金の公開が必要だと思います', 'session_id': 2},
        {'content': 'DXの推進に期待しています', 'session_id': 3},
        {'content': 'デジタル化を進めてほしい', 'session_id': 4},
        {'content': '選挙制度の改革が必要です', 'session_id': 5},
        {'content': '投票率の向上に取り組むべき', 'session_id': 6},
    ]
    
    categorizer = EnhancedCategorizer()
    
    print("=== Enhanced Categorization Test ===\n")
    
    # Test keyword extraction
    print("Top Keywords:")
    keywords = categorizer.extract_top_keywords(sample_responses, n_keywords=10)
    for keyword, score in keywords:
        print(f"  {keyword}: {score:.3f}")
    print()
    
    # Test clustering
    print("Clustering Results:")
    categories = categorizer.categorize_by_clustering(sample_responses)
    for category, responses in categories.items():
        print(f"\n{category} ({len(responses)}件):")
        for resp in responses:
            print(f"  - {resp['content']}")


if __name__ == '__main__':
    test_enhanced_categorization()









