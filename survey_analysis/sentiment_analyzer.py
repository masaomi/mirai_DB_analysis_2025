#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sentiment Analyzer Module
日本語テキストの感情分析（肯定/否定/中立）
"""

import re
from typing import Dict, List, Tuple


class SentimentAnalyzer:
    """
    Japanese sentiment analyzer using keyword-based approach
    """
    
    def __init__(self):
        # Positive keywords
        self.positive_keywords = {
            '良い', 'いい', 'よい', '素晴らしい', '最高', '期待', '希望', '賛成', '嬉しい',
            '楽しみ', 'ありがたい', '素敵', '好き', '好ましい', '満足', '成功', '改善',
            '進歩', '発展', '向上', '効果的', '有効', '便利', '役立つ', '優れた',
            '素晴らしい', '喜ばしい', '歓迎', 'メリット', '利点', '効率', 'スムーズ',
            '簡単', '明快', '分かりやすい', '透明', '公正', '適切', '必要', '重要',
            '推進', '支持', '応援', 'ポジティブ', '前向き', '可能', '実現', '達成'
        }
        
        # Negative keywords
        self.negative_keywords = {
            '悪い', 'わるい', 'ダメ', 'だめ', '問題', '課題', '懸念', '心配', '不安',
            '危険', 'リスク', '反対', '困る', '難しい', '複雑', '不便', '無駄', '無意味',
            '失敗', '減少', '低下', '悪化', '不満', '不快', '嫌', '嫌い', '残念', '遺憾',
            '後悔', '不適切', '不公平', '不透明', 'デメリット', '欠点', '弱点',
            '非効率', '混乱', '遅い', '分かりにくい', '難解', '疑問', '疑念', '批判',
            '否定', 'ネガティブ', '不可能', '阻害', '妨げ', '障害', '困難'
        }
        
        # Intensifiers (increase sentiment strength)
        self.intensifiers = {
            'とても', '非常に', 'すごく', 'かなり', '本当に', 'まさに', '極めて',
            'ものすごく', '大変', '著しく', '顕著に'
        }
        
        # Negation words (reverse sentiment)
        self.negations = {
            'ない', 'ず', 'ぬ', 'ません', 'ん', 'なく', 'なし'
        }
    
    def analyze(self, text: str) -> Dict[str, any]:
        """
        Analyze sentiment of given text
        
        Args:
            text: Input text to analyze
            
        Returns:
            Dictionary containing:
            - sentiment: 'positive', 'negative', or 'neutral'
            - score: sentiment score (-1.0 to 1.0)
            - positive_count: number of positive keywords found
            - negative_count: number of negative keywords found
            - confidence: confidence level (0.0 to 1.0)
        """
        text = text.lower()
        
        # Count positive and negative keywords
        positive_count = sum(1 for keyword in self.positive_keywords if keyword in text)
        negative_count = sum(1 for keyword in self.negative_keywords if keyword in text)
        
        # Check for intensifiers
        intensifier_count = sum(1 for intensifier in self.intensifiers if intensifier in text)
        intensity_multiplier = 1 + (intensifier_count * 0.3)
        
        # Check for negations (simplified)
        has_negation = any(neg in text for neg in self.negations)
        
        # Calculate raw score
        raw_score = (positive_count - negative_count) * intensity_multiplier
        
        # Apply negation (reverse if strong negation pattern detected)
        if has_negation and abs(raw_score) > 0:
            # Simple heuristic: if negation exists near sentiment words, consider reversing
            # This is a simplified approach
            pass  # Keep original for now (more sophisticated negation handling needed)
        
        # Normalize score to -1.0 to 1.0
        max_count = max(positive_count + negative_count, 1)
        normalized_score = max(-1.0, min(1.0, raw_score / max_count))
        
        # Determine sentiment category
        if normalized_score > 0.1:
            sentiment = 'positive'
        elif normalized_score < -0.1:
            sentiment = 'negative'
        else:
            sentiment = 'neutral'
        
        # Calculate confidence based on keyword density
        total_keywords = positive_count + negative_count
        confidence = min(1.0, total_keywords / 5.0)  # Max confidence at 5+ keywords
        
        return {
            'sentiment': sentiment,
            'score': normalized_score,
            'positive_count': positive_count,
            'negative_count': negative_count,
            'confidence': confidence
        }
    
    def analyze_batch(self, texts: List[str]) -> List[Dict[str, any]]:
        """
        Analyze sentiment for multiple texts
        
        Args:
            texts: List of texts to analyze
            
        Returns:
            List of sentiment analysis results
        """
        return [self.analyze(text) for text in texts]
    
    def get_sentiment_distribution(self, texts: List[str]) -> Dict[str, int]:
        """
        Get distribution of sentiments in a collection of texts
        
        Args:
            texts: List of texts to analyze
            
        Returns:
            Dictionary with counts for each sentiment category
        """
        results = self.analyze_batch(texts)
        distribution = {'positive': 0, 'negative': 0, 'neutral': 0}
        
        for result in results:
            distribution[result['sentiment']] += 1
        
        return distribution


def test_sentiment_analyzer():
    """Test function for sentiment analyzer"""
    analyzer = SentimentAnalyzer()
    
    test_cases = [
        "この政策は素晴らしいと思います。期待しています。",
        "問題が多すぎて心配です。反対です。",
        "これについては特に意見がありません。",
        "とても良い取り組みだと感じています。",
        "非常に懸念すべき状況だと思います。"
    ]
    
    print("=== Sentiment Analysis Test ===\n")
    for text in test_cases:
        result = analyzer.analyze(text)
        print(f"Text: {text}")
        print(f"Sentiment: {result['sentiment']}")
        print(f"Score: {result['score']:.2f}")
        print(f"Confidence: {result['confidence']:.2f}")
        print()


if __name__ == '__main__':
    test_sentiment_analyzer()



















