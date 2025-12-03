"""Detect stance (for/against/neutral) from responses."""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

from pipeline.extractors.response_extractor import UserResponse


class Stance(str, Enum):
    """Stance categories."""
    FOR = "賛成"
    AGAINST = "反対"
    NEUTRAL = "中立/不明"
    CONDITIONAL = "条件付き"


@dataclass
class StanceResult:
    """Result of stance detection for a single response."""
    session_id: str
    content: str
    stance: Stance
    confidence: float
    keywords_found: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "content": self.content[:200] + "..." if len(self.content) > 200 else self.content,
            "stance": self.stance.value,
            "confidence": self.confidence,
            "keywords_found": self.keywords_found,
        }


# Japanese keywords for stance detection
POSITIVE_KEYWORDS = [
    "賛成", "良い", "期待", "必要", "推進", "支持", "進めるべき",
    "同意", "効果的", "有効", "便利", "メリット", "正しい",
    "素晴らしい", "すばらしい", "いいと思う", "良いと思う",
    "前向き", "ポジティブ", "歓迎", "うれしい", "嬉しい",
    "やるべき", "すべき", "望ましい", "期待している",
]

NEGATIVE_KEYWORDS = [
    "反対", "懸念", "心配", "問題", "リスク", "危険", "不要",
    "課題", "難しい", "デメリット", "慎重", "疑問", "不安",
    "よくない", "良くない", "ダメ", "だめ", "無理",
    "やめるべき", "避けるべき", "望ましくない",
    "悪い", "まずい", "困る", "怖い", "恐れ",
]

CONDITIONAL_KEYWORDS = [
    "条件付き", "場合による", "一概には", "ケースバイケース",
    "どちらとも", "両方", "メリットデメリット", "一長一短",
    "ただし", "但し", "しかし", "ただ", "でも",
    "もし", "仮に", "条件次第", "状況による",
]


class StanceDetector:
    """Detect stance from response content."""
    
    def __init__(
        self,
        positive_keywords: Optional[List[str]] = None,
        negative_keywords: Optional[List[str]] = None,
        conditional_keywords: Optional[List[str]] = None,
    ):
        """Initialize stance detector.
        
        Args:
            positive_keywords: Override positive keywords
            negative_keywords: Override negative keywords
            conditional_keywords: Override conditional keywords
        """
        self.positive_keywords = positive_keywords or POSITIVE_KEYWORDS
        self.negative_keywords = negative_keywords or NEGATIVE_KEYWORDS
        self.conditional_keywords = conditional_keywords or CONDITIONAL_KEYWORDS
    
    def detect_stance(self, content: str) -> Tuple[Stance, float, List[str]]:
        """Detect stance from text content.
        
        Args:
            content: Response text
            
        Returns:
            Tuple of (stance, confidence, keywords_found)
        """
        content_lower = content.lower()
        
        # Find matching keywords
        pos_found = [k for k in self.positive_keywords if k in content_lower]
        neg_found = [k for k in self.negative_keywords if k in content_lower]
        cond_found = [k for k in self.conditional_keywords if k in content_lower]
        
        pos_count = len(pos_found)
        neg_count = len(neg_found)
        cond_count = len(cond_found)
        total = pos_count + neg_count + cond_count
        
        # No keywords found
        if total == 0:
            return Stance.NEUTRAL, 0.3, []
        
        # Check for conditional stance
        if cond_count > 0 and (pos_count > 0 or neg_count > 0):
            confidence = cond_count / total
            return Stance.CONDITIONAL, min(confidence + 0.3, 0.8), cond_found
        
        # Determine primary stance
        if pos_count > neg_count:
            confidence = pos_count / (pos_count + neg_count) if (pos_count + neg_count) > 0 else 0.5
            return Stance.FOR, confidence, pos_found
        elif neg_count > pos_count:
            confidence = neg_count / (pos_count + neg_count) if (pos_count + neg_count) > 0 else 0.5
            return Stance.AGAINST, confidence, neg_found
        else:
            # Equal positive and negative
            return Stance.NEUTRAL, 0.5, pos_found + neg_found
    
    def analyze_responses(
        self,
        responses: List[UserResponse]
    ) -> List[StanceResult]:
        """Analyze stances for all responses.
        
        Args:
            responses: List of user responses
            
        Returns:
            List of StanceResult objects
        """
        results = []
        for resp in responses:
            stance, confidence, keywords = self.detect_stance(resp.content)
            results.append(StanceResult(
                session_id=resp.session_id,
                content=resp.content,
                stance=stance,
                confidence=confidence,
                keywords_found=keywords,
            ))
        return results
    
    def get_stance_distribution(
        self,
        results: List[StanceResult]
    ) -> Dict[str, Dict[str, Any]]:
        """Get distribution of stances.
        
        Args:
            results: List of stance results
            
        Returns:
            Dictionary with stance counts and percentages
        """
        if not results:
            return {}
        
        counts = {stance.value: 0 for stance in Stance}
        
        for r in results:
            counts[r.stance.value] += 1
        
        total = len(results)
        distribution = {}
        
        for stance_name, count in counts.items():
            distribution[stance_name] = {
                "count": count,
                "percentage": (count / total) * 100 if total > 0 else 0,
            }
        
        return distribution
    
    def get_responses_by_stance(
        self,
        results: List[StanceResult]
    ) -> Dict[str, List[StanceResult]]:
        """Group results by stance.
        
        Args:
            results: List of stance results
            
        Returns:
            Dictionary mapping stance to list of results
        """
        grouped = {stance.value: [] for stance in Stance}
        
        for r in results:
            grouped[r.stance.value].append(r)
        
        return grouped

