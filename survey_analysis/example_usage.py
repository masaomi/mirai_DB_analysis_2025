#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Usage Examples for Enhanced Survey Analysis
使用例スクリプト
"""

import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from sentiment_analyzer import SentimentAnalyzer
from intent_extractor import IntentExtractor
from enhanced_categorization import EnhancedCategorizer


def example_sentiment_analysis():
    """Example: Sentiment analysis"""
    print("="*60)
    print("Example 1: Sentiment Analysis")
    print("="*60 + "\n")
    
    analyzer = SentimentAnalyzer()
    
    test_texts = [
        "この政策は素晴らしいと思います。期待しています。",
        "問題が多すぎて心配です。反対です。",
        "これについては特に意見がありません。",
    ]
    
    for text in test_texts:
        result = analyzer.analyze(text)
        print(f"Text: {text}")
        print(f"  Sentiment: {result['sentiment']}")
        print(f"  Score: {result['score']:.2f}")
        print(f"  Confidence: {result['confidence']:.2f}")
        print()


def example_intent_extraction():
    """Example: Intent extraction"""
    print("="*60)
    print("Example 2: Intent Extraction")
    print("="*60 + "\n")
    
    extractor = IntentExtractor()
    
    test_texts = [
        "政治の透明性を向上させてほしいと思います。",
        "DXの推進が心配です。セキュリティが問題になるのではないでしょうか。",
        "まず政治資金の完全公開を実現すべきだと考えます。",
    ]
    
    for text in test_texts:
        result = extractor.extract_intent(text)
        print(f"Text: {text}")
        print(f"  Primary Intent: {result['primary_intent']}")
        print(f"  All Intents: {result['all_intents']}")
        print(f"  Topics: {result['topics']}")
        print(f"  Has Desire: {result['has_desire']}")
        print(f"  Has Concern: {result['has_concern']}")
        print()


def example_categorization():
    """Example: TF-IDF + Clustering categorization"""
    print("="*60)
    print("Example 3: TF-IDF + Clustering Categorization")
    print("="*60 + "\n")
    
    categorizer = EnhancedCategorizer()
    
    # Sample responses
    sample_responses = [
        {'content': '政治の透明性を高めることが重要です', 'id': 1},
        {'content': '政治資金の公開が必要だと思います', 'id': 2},
        {'content': 'DXの推進に期待しています', 'id': 3},
        {'content': 'デジタル化を進めてほしい', 'id': 4},
        {'content': '選挙制度の改革が必要です', 'id': 5},
        {'content': '投票率の向上に取り組むべき', 'id': 6},
        {'content': '政治資金規正法の見直しを', 'id': 7},
        {'content': '透明性の確保が最優先', 'id': 8},
    ]
    
    # Extract keywords
    print("Top Keywords:")
    keywords = categorizer.extract_top_keywords(sample_responses, n_keywords=10)
    for keyword, score in keywords:
        print(f"  {keyword}: {score:.3f}")
    print()
    
    # Categorize
    print("Categories:")
    categories = categorizer.categorize_by_clustering(sample_responses)
    for category_name, responses in categories.items():
        print(f"\n{category_name} ({len(responses)}件):")
        for resp in responses:
            print(f"  - {resp['content']}")


def example_full_pipeline():
    """Example: Full analysis pipeline on small dataset"""
    print("="*60)
    print("Example 4: Full Analysis Pipeline")
    print("="*60 + "\n")
    
    # Sample data
    responses = [
        {'content': '政治の透明性を高めてほしい', 'id': 1},
        {'content': '政治資金の公開に賛成です', 'id': 2},
        {'content': 'DXの推進が心配です', 'id': 3},
        {'content': 'デジタル化は良いことだと思います', 'id': 4},
    ]
    
    # Initialize modules
    sentiment_analyzer = SentimentAnalyzer()
    intent_extractor = IntentExtractor()
    categorizer = EnhancedCategorizer()
    
    # Categorize
    categories = categorizer.categorize_by_clustering(responses)
    
    print("Full Analysis Results:\n")
    
    for category_name, category_responses in categories.items():
        print(f"Category: {category_name}")
        print(f"  Count: {len(category_responses)}")
        
        # Analyze sentiment
        sentiments = [sentiment_analyzer.analyze(r['content']) for r in category_responses]
        positive_count = sum(1 for s in sentiments if s['sentiment'] == 'positive')
        negative_count = sum(1 for s in sentiments if s['sentiment'] == 'negative')
        neutral_count = sum(1 for s in sentiments if s['sentiment'] == 'neutral')
        
        print(f"  Sentiment: Positive={positive_count}, Negative={negative_count}, Neutral={neutral_count}")
        
        # Analyze intent
        intents = [intent_extractor.extract_intent(r['content']) for r in category_responses]
        desire_count = sum(1 for i in intents if i['has_desire'])
        concern_count = sum(1 for i in intents if i['has_concern'])
        
        print(f"  Intent: Desires={desire_count}, Concerns={concern_count}")
        
        # Sample responses
        print(f"  Samples:")
        for resp in category_responses[:2]:
            print(f"    - {resp['content']}")
        print()


def main():
    """Run all examples"""
    examples = [
        ("Sentiment Analysis", example_sentiment_analysis),
        ("Intent Extraction", example_intent_extraction),
        ("TF-IDF Categorization", example_categorization),
        ("Full Pipeline", example_full_pipeline),
    ]
    
    print("\n" + "="*60)
    print("Enhanced Survey Analysis - Usage Examples")
    print("="*60 + "\n")
    
    if len(sys.argv) > 1:
        # Run specific example
        example_num = int(sys.argv[1]) - 1
        if 0 <= example_num < len(examples):
            name, func = examples[example_num]
            func()
        else:
            print(f"Invalid example number. Choose 1-{len(examples)}")
    else:
        # Run all examples
        for name, func in examples:
            func()
            print("\n")


if __name__ == '__main__':
    main()



















