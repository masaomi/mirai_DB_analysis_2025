#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Intent Extractor Module
回答者の意図（要望、懸念、提案等）を抽出
"""

import re
from typing import Dict, List, Set
from collections import defaultdict


class IntentExtractor:
    """
    Extract intents from Japanese text responses
    """
    
    def __init__(self):
        # Intent patterns (regex patterns for different intent types)
        self.intent_patterns = {
            'desire': [
                # 要望・希望パターン
                r'(.{0,30})(したい|してほしい|してもらいたい|願う|希望|期待)',
                r'(.{0,30})(であってほしい|になってほしい|になりたい)',
                r'(.{0,30})(を求める|が必要|がほしい)',
            ],
            'concern': [
                # 懸念・心配パターン
                r'(.{0,30})(が心配|が不安|が懸念|を懸念|が問題|が課題)',
                r'(.{0,30})(危険|リスク|恐れ|怖い)',
                r'(.{0,30})(どうなる|大丈夫|心配)',
            ],
            'proposal': [
                # 提案パターン
                r'(.{0,30})(すべき|すべきだ|する必要がある|が必要)',
                r'(.{0,30})(提案|提言|推進|実現|改善)',
                r'(.{0,30})(を進める|を行う|を実施|導入)',
            ],
            'opinion': [
                # 意見・評価パターン
                r'(.{0,30})(と思う|と考える|と感じる)',
                r'(.{0,30})(だと思います|だと考えます|だと感じます)',
                r'(.{0,30})(という印象|という感想)',
            ],
            'question': [
                # 質問・疑問パターン
                r'(.{0,30})(でしょうか|ですか|なのか|だろうか)',
                r'(.{0,30})(わからない|不明|疑問)',
            ],
            'experience': [
                # 経験・事実パターン
                r'(.{0,30})(した|している|してきた)',
                r'(.{0,30})(だった|でした|がある|がない)',
            ],
            'support': [
                # 支持・賛成パターン
                r'(.{0,30})(賛成|支持|応援|同意)',
                r'(.{0,30})(良い|素晴らしい|すばらしい)',
            ],
            'opposition': [
                # 反対パターン
                r'(.{0,30})(反対|否定|やめる|やめて)',
            ],
        }
        
        # Topic keywords for deeper understanding
        self.topic_keywords = {
            'politics': ['政治', '政策', '議員', '国会', '選挙', '投票', '法案', '政権', '与党', '野党'],
            'transparency': ['透明', '公開', '見える', '可視化', '情報', '開示'],
            'digital': ['DX', 'デジタル', 'IT', 'システム', 'オンライン', 'web', 'アプリ'],
            'money': ['政治資金', '献金', 'お金', '資金', '財務', 'コスト', '費用'],
            'corruption': ['汚職', '不正', '腐敗', '癒着', '利権'],
            'society': ['国民', '庶民', '市民', '生活', '暮らし', '社会'],
            'security': ['安全', '安心', 'セキュリティ', '保護', '防衛'],
            'efficiency': ['効率', '迅速', 'スピード', '簡単', '便利'],
        }
    
    def extract_intent(self, text: str) -> Dict[str, any]:
        """
        Extract intents from text
        
        Args:
            text: Input text to analyze
            
        Returns:
            Dictionary containing:
            - primary_intent: main intent type
            - all_intents: list of all detected intents
            - intent_phrases: dict of intent type to extracted phrases
            - topics: list of detected topics
        """
        text_lower = text.lower()
        
        # Extract all matching intents
        intent_matches = defaultdict(list)
        
        for intent_type, patterns in self.intent_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    # Extract the context around the pattern
                    context = match.group(1) if match.group(1) else match.group(0)
                    intent_matches[intent_type].append(context.strip())
        
        # Identify topics
        detected_topics = []
        for topic, keywords in self.topic_keywords.items():
            if any(keyword in text for keyword in keywords):
                detected_topics.append(topic)
        
        # Determine primary intent (most common or first detected)
        all_intents = list(intent_matches.keys())
        primary_intent = all_intents[0] if all_intents else 'statement'
        
        return {
            'primary_intent': primary_intent,
            'all_intents': all_intents,
            'intent_phrases': dict(intent_matches),
            'topics': detected_topics,
            'has_desire': 'desire' in all_intents,
            'has_concern': 'concern' in all_intents,
            'has_proposal': 'proposal' in all_intents,
        }
    
    def extract_key_phrases(self, text: str, max_phrases: int = 5) -> List[str]:
        """
        Extract key phrases from text using simple heuristics
        
        Args:
            text: Input text
            max_phrases: Maximum number of phrases to extract
            
        Returns:
            List of key phrases
        """
        # Split by common sentence delimiters
        sentences = re.split(r'[。、！？\n]', text)
        
        # Filter and clean sentences
        phrases = []
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 5 and len(sentence) < 100:
                phrases.append(sentence)
        
        return phrases[:max_phrases]
    
    def categorize_by_intent(self, responses: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Categorize responses by their primary intent
        
        Args:
            responses: List of response dictionaries with 'content' field
            
        Returns:
            Dictionary mapping intent types to responses
        """
        categorized = defaultdict(list)
        
        for response in responses:
            content = response.get('content', '')
            intent_result = self.extract_intent(content)
            primary_intent = intent_result['primary_intent']
            
            # Add intent information to response
            response_with_intent = response.copy()
            response_with_intent['intent_info'] = intent_result
            
            categorized[primary_intent].append(response_with_intent)
        
        return dict(categorized)
    
    def get_intent_summary(self, responses: List[Dict]) -> Dict[str, any]:
        """
        Get summary statistics about intents in responses
        
        Args:
            responses: List of response dictionaries
            
        Returns:
            Summary statistics
        """
        intent_counts = defaultdict(int)
        topic_counts = defaultdict(int)
        
        total = len(responses)
        
        for response in responses:
            content = response.get('content', '')
            intent_result = self.extract_intent(content)
            
            # Count primary intent
            intent_counts[intent_result['primary_intent']] += 1
            
            # Count all intents
            for intent in intent_result['all_intents']:
                intent_counts[f"any_{intent}"] += 1
            
            # Count topics
            for topic in intent_result['topics']:
                topic_counts[topic] += 1
        
        return {
            'total_responses': total,
            'intent_counts': dict(intent_counts),
            'topic_counts': dict(topic_counts),
            'desire_rate': intent_counts.get('any_desire', 0) / total if total > 0 else 0,
            'concern_rate': intent_counts.get('any_concern', 0) / total if total > 0 else 0,
            'proposal_rate': intent_counts.get('any_proposal', 0) / total if total > 0 else 0,
        }


def test_intent_extractor():
    """Test function for intent extractor"""
    extractor = IntentExtractor()
    
    test_cases = [
        "政治の透明性を向上させてほしいと思います。",
        "DXの推進が心配です。セキュリティが問題になるのではないでしょうか。",
        "まず政治資金の完全公開を実現すべきだと考えます。",
        "選挙制度改革について賛成です。国民のための政治を期待しています。",
        "この法案には反対です。もっと慎重に検討する必要があります。",
    ]
    
    print("=== Intent Extraction Test ===\n")
    for text in test_cases:
        result = extractor.extract_intent(text)
        print(f"Text: {text}")
        print(f"Primary Intent: {result['primary_intent']}")
        print(f"All Intents: {result['all_intents']}")
        print(f"Topics: {result['topics']}")
        print(f"Has Desire: {result['has_desire']}")
        print(f"Has Concern: {result['has_concern']}")
        print(f"Has Proposal: {result['has_proposal']}")
        print()


if __name__ == '__main__':
    test_intent_extractor()











