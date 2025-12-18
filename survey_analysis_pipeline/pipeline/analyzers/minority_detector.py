"""Detect minority/outlier opinions that may be important."""

import asyncio
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from collections import Counter
import numpy as np

from pipeline.extractors.response_extractor import UserResponse
from config.settings import Settings, get_settings

if TYPE_CHECKING:
    from core.llm_client import LLMClient


RELEVANCE_PROMPT = """以下の意見が「{survey_title}」に関連する法案検討に参考になる実質的な意見かどうか厳格に判定してください。

## 意見
{content}

## 除外基準（relevant: false）- 以下に該当する場合は必ず除外
1. **挨拶・謝辞・激励のみ**：「ありがとう」「お疲れ様」「頑張ってください」「応援しています」等
2. **インタビュー・システムへのコメント**：「質問の仕方が〜」「AIの回答が〜」「学習データが〜」「時間が増えた」等
3. **空虚・意味のない回答**：「わからない」「特になし」「あああ」等
4. **テーマと完全に無関係**：法案の内容に一切触れていない話題
5. **政党・選挙への一般的応援**：法案の具体的内容に言及しない単なる応援
6. **単なる感想・印象のみ**：「面白い」「難しい」など具体的な論点がない

## 採用基準（relevant: true）- 以下のいずれかを満たす場合のみ採用
- 法案・テーマに対する具体的な賛否理由がある
- 実務上の課題・懸念点・メリットの具体的指摘がある
- 専門知識・実務経験・当事者経験に基づく意見がある
- 法制審議会での論点に関連する具体的意見がある

## 出力形式
JSON形式で出力してください：
{{"relevant": true または false, "reason": "判定理由を簡潔に", "exclusion_category": "除外の場合のカテゴリ"}}
"""


@dataclass
class MinorityOpinion:
    """A minority opinion with importance score."""
    content: str
    session_id: str
    outlier_score: float
    uniqueness_reason: str
    unique_keywords: List[str] = field(default_factory=list)
    distance_from_centroid: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "content": self.content,
            "session_id": self.session_id,
            "outlier_score": round(self.outlier_score, 3),
            "uniqueness_reason": self.uniqueness_reason,
            "unique_keywords": self.unique_keywords,
            "distance_from_centroid": round(self.distance_from_centroid, 3),
        }


class MinorityDetector:
    """Detect minority opinions using multiple methods."""
    
    def __init__(self, settings: Optional[Settings] = None):
        """Initialize detector.
        
        Args:
            settings: Application settings
        """
        self.settings = settings or get_settings()
        self._embedder = None
    
    @property
    def embedder(self):
        """Lazy load sentence transformer."""
        if self._embedder is None:
            from sentence_transformers import SentenceTransformer
            self._embedder = SentenceTransformer(self.settings.embedding_model)
        return self._embedder
    
    def detect_minorities(
        self,
        responses: List[UserResponse],
        top_n: Optional[int] = None,
        min_score: float = 0.5,
    ) -> List[MinorityOpinion]:
        """Detect minority opinions using multiple methods.
        
        Methods used:
        1. TF-IDF based uniqueness (rare terms)
        2. Semantic distance from centroid
        3. Unique keyword detection
        
        Args:
            responses: List of user responses
            top_n: Number of minorities to return (overrides settings)
            min_score: Minimum outlier score
            
        Returns:
            List of MinorityOpinion objects sorted by score
        """
        if len(responses) < 5:
            return []
        
        top_n = top_n or self.settings.minority_top_n
        
        contents = [r.content for r in responses]
        
        # Method 1: Semantic distance from centroid
        distance_scores = self._compute_centroid_distances(contents)
        
        # Method 2: TF-IDF uniqueness
        tfidf_scores, unique_terms = self._compute_tfidf_uniqueness(contents)
        
        # Method 3: Rare keyword detection
        keyword_scores, rare_keywords = self._detect_rare_keywords(contents)
        
        # Combine scores
        results = []
        for i, resp in enumerate(responses):
            # Weighted combination of scores
            combined_score = (
                0.5 * distance_scores[i] +
                0.3 * tfidf_scores[i] +
                0.2 * keyword_scores[i]
            )
            
            # Determine uniqueness reason
            if distance_scores[i] > 0.6:
                reason = "主流意見と異なる視点"
            elif len(rare_keywords.get(i, [])) > 2:
                reason = "独自のキーワード/専門的視点"
            elif tfidf_scores[i] > 0.5:
                reason = "ユニークな表現"
            else:
                reason = "中程度のユニークさ"
            
            results.append(MinorityOpinion(
                content=resp.content,
                session_id=resp.session_id,
                outlier_score=combined_score,
                uniqueness_reason=reason,
                unique_keywords=rare_keywords.get(i, [])[:5],
                distance_from_centroid=distance_scores[i],
            ))
        
        # Sort by score and filter
        results.sort(key=lambda x: x.outlier_score, reverse=True)
        filtered = [r for r in results if r.outlier_score >= min_score]
        
        return filtered[:top_n]
    
    def _compute_centroid_distances(self, contents: List[str]) -> List[float]:
        """Compute distance from centroid for each response.
        
        Args:
            contents: List of response texts
            
        Returns:
            List of normalized distance scores (0-1)
        """
        from sklearn.metrics.pairwise import cosine_similarity
        
        # Get embeddings
        embeddings = self.embedder.encode(
            contents,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        
        # Compute centroid
        centroid = embeddings.mean(axis=0).reshape(1, -1)
        
        # Compute distances
        similarities = cosine_similarity(embeddings, centroid).flatten()
        distances = 1 - similarities
        
        # Normalize to 0-1
        if distances.max() > distances.min():
            distances = (distances - distances.min()) / (distances.max() - distances.min())
        
        return distances.tolist()
    
    def _compute_tfidf_uniqueness(
        self,
        contents: List[str]
    ) -> tuple[List[float], Dict[int, List[str]]]:
        """Compute TF-IDF based uniqueness scores.
        
        Args:
            contents: List of response texts
            
        Returns:
            Tuple of (scores, unique_terms_per_document)
        """
        from sklearn.feature_extraction.text import TfidfVectorizer
        
        try:
            vectorizer = TfidfVectorizer(
                max_features=1000,
                token_pattern=r'(?u)\b\w+\b',
                min_df=1,
                max_df=0.8,
            )
            
            tfidf_matrix = vectorizer.fit_transform(contents)
            feature_names = vectorizer.get_feature_names_out()
            
            # Compute average TF-IDF score per document
            scores = []
            unique_terms = {}
            
            for i in range(tfidf_matrix.shape[0]):
                doc_vector = tfidf_matrix[i].toarray().flatten()
                
                # Average score (higher = more unique terms)
                nonzero = doc_vector[doc_vector > 0]
                avg_score = nonzero.mean() if len(nonzero) > 0 else 0
                scores.append(avg_score)
                
                # Get terms with high TF-IDF
                high_tfidf_indices = np.where(doc_vector > 0.3)[0]
                unique_terms[i] = [feature_names[j] for j in high_tfidf_indices]
            
            # Normalize scores
            max_score = max(scores) if scores else 1
            scores = [s / max_score if max_score > 0 else 0 for s in scores]
            
            return scores, unique_terms
            
        except Exception:
            return [0.0] * len(contents), {}
    
    def _detect_rare_keywords(
        self,
        contents: List[str]
    ) -> tuple[List[float], Dict[int, List[str]]]:
        """Detect rare keywords in each response.
        
        Args:
            contents: List of response texts
            
        Returns:
            Tuple of (scores, rare_keywords_per_document)
        """
        # Tokenize all content
        all_words = []
        doc_words = []
        
        for content in contents:
            words = content.split()
            doc_words.append(words)
            all_words.extend(words)
        
        # Count word frequencies
        word_counts = Counter(all_words)
        total_docs = len(contents)
        
        # Threshold for rare words (appear in less than 5% of responses)
        rare_threshold = max(2, int(total_docs * 0.05))
        
        scores = []
        rare_keywords = {}
        
        for i, words in enumerate(doc_words):
            # Find rare words in this document
            rare = [
                w for w in set(words)
                if word_counts.get(w, 0) <= rare_threshold
                and len(w) > 1
            ]
            
            rare_keywords[i] = rare
            
            # Score based on proportion of rare words
            score = len(rare) / len(words) if words else 0
            scores.append(min(score * 2, 1.0))  # Scale up but cap at 1
        
        return scores, rare_keywords
    
    def get_minority_summary(
        self,
        minorities: List[MinorityOpinion]
    ) -> Dict[str, Any]:
        """Get summary of detected minorities.
        
        Args:
            minorities: List of minority opinions
            
        Returns:
            Summary dictionary
        """
        if not minorities:
            return {
                "count": 0,
                "avg_score": 0,
                "reasons": {},
                "minorities": [],
            }
        
        # Count reasons
        reasons = Counter(m.uniqueness_reason for m in minorities)
        
        return {
            "count": len(minorities),
            "avg_score": sum(m.outlier_score for m in minorities) / len(minorities),
            "reasons": dict(reasons),
            "minorities": [m.to_dict() for m in minorities],
        }
    
    async def filter_by_relevance(
        self,
        minorities: List[MinorityOpinion],
        survey_title: str,
        llm_client: "LLMClient",
    ) -> List[MinorityOpinion]:
        """Filter minority opinions by relevance to the survey topic using LLM.
        
        Args:
            minorities: List of minority opinions to filter
            survey_title: Title of the survey for context
            llm_client: LLM client for relevance checking
            
        Returns:
            List of relevant minority opinions (limited to minority_top_n)
        """
        if not minorities:
            return []
        
        async def check_relevance(opinion: MinorityOpinion) -> tuple[MinorityOpinion, bool]:
            """Check if a single opinion is relevant."""
            prompt = RELEVANCE_PROMPT.format(
                survey_title=survey_title,
                content=opinion.content[:500],  # Truncate for efficiency
            )
            
            try:
                response = await llm_client.generate(prompt)
                
                # Parse JSON response
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    data = json.loads(response[json_start:json_end])
                    is_relevant = data.get("relevant", False)  # Default to False for stricter filtering
                    return (opinion, is_relevant)
                else:
                    # If parsing fails, exclude by default
                    return (opinion, False)
            except Exception as e:
                # On error, exclude by default for stricter filtering
                return (opinion, False)
        
        # Check all opinions in parallel
        tasks = [check_relevance(m) for m in minorities]
        results = await asyncio.gather(*tasks)
        
        # Filter to keep only relevant opinions
        relevant = [opinion for opinion, is_relevant in results if is_relevant]
        
        # Apply top_n limit after relevance filtering
        return relevant[:self.settings.minority_top_n]
    
    def filter_by_relevance_sync(
        self,
        minorities: List[MinorityOpinion],
        survey_title: str,
        llm_client: "LLMClient",
    ) -> List[MinorityOpinion]:
        """Synchronous wrapper for filter_by_relevance."""
        return asyncio.run(self.filter_by_relevance(minorities, survey_title, llm_client))

