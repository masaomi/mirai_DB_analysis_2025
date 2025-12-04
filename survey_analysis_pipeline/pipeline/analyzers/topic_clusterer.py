"""Cluster responses by topic using embeddings."""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set
import numpy as np

from pipeline.extractors.response_extractor import UserResponse
from config.settings import Settings, get_settings


# Japanese stopwords - common words that don't carry topic meaning
JAPANESE_STOPWORDS: Set[str] = {
    # Particles and conjunctions
    "また", "ただ", "しかし", "ただし", "なお", "けど", "けれども", "でも",
    "それで", "そして", "だから", "ので", "のに", "ため", "から", "まで",
    "より", "ほど", "くらい", "など", "とか", "やら", "なり", "つまり",
    "すなわち", "あるいは", "または", "もしくは", "ならびに", "および",
    # Fillers and responses
    "はい", "ええ", "うん", "いいえ", "いや", "いえ", "なるほど", "そうですね",
    "そうですか", "そうなんですね", "そう", "ですね", "ですか", "ですが",
    "ああ", "おお", "ふむ", "へえ", "まあ", "えーと", "あの", "その",
    "うーん", "えー", "んー", "あー", "おー", "えっと", "まぁ",
    "そうです", "そうですよね", "そうだと思います", "わかりました",
    "ごめんなさい", "すみません", "申し訳", "ありがとう", "よろしく",
    "ありがとうございました", "ありがとうございます", "頑張ってください",
    "こちらこそ", "こちらこそありがとうございました", "お願いします",
    "失礼します", "失礼しました", "よろしくお願いします",
    # Pronouns and demonstratives
    "これ", "それ", "あれ", "どれ", "この", "その", "あの", "どの",
    "ここ", "そこ", "あそこ", "どこ", "こちら", "そちら", "あちら",
    "わたし", "私", "僕", "俺", "自分", "あなた", "彼", "彼女",
    # Common verbs (conjugated forms)
    "する", "します", "した", "しました", "される", "できる", "できます",
    "ある", "あります", "あった", "ありました", "ない", "ありません",
    "いる", "います", "いた", "いました", "いない", "いません",
    "なる", "なります", "なった", "なりました", "思う", "思います",
    "思った", "思いました", "言う", "言います", "言った", "言いました",
    "知る", "知ります", "知った", "知りました", "知らない", "知りません",
    "見る", "見ます", "見た", "見ました", "聞く", "聞きます", "聞いた",
    "考える", "考えます", "考えた", "使う", "使います", "持つ", "持ちます",
    # Common adjectives
    "いい", "良い", "よい", "悪い", "多い", "少ない", "大きい", "小さい",
    "高い", "低い", "長い", "短い", "新しい", "古い", "難しい", "易しい",
    # Common adverbs and discourse markers
    "とても", "非常に", "かなり", "少し", "ちょっと", "もう", "まだ",
    "すでに", "やはり", "やっぱり", "もっと", "さらに", "特に", "全く",
    "本当に", "実際", "実際に", "基本的に", "一般的に", "具体的に",
    "例えば", "たとえば", "あと", "まず", "次に", "最後に", "では",
    "ところで", "さて", "ちなみに", "要するに", "結局", "結局は",
    "確かに", "もちろん", "当然", "おそらく", "たぶん", "多分", "きっと",
    # Generic expressions
    "こと", "もの", "ところ", "わけ", "よう", "ほう", "はず", "つもり",
    "点", "面", "部分", "場合", "時", "方", "人", "形", "感じ",
    "意味", "理由", "結果", "影響", "問題", "必要", "可能", "重要",
    "状況", "状態", "内容", "程度", "範囲", "対象", "関係", "観点",
    # Question/answer patterns
    "何", "なに", "どう", "どのように", "なぜ", "どうして", "いつ", "どこで",
    # Numbers and counters
    "一つ", "二つ", "三つ", "一", "二", "三", "年", "月", "日",
    # Other common words
    "今", "前", "後", "中", "上", "下", "間", "次", "最初", "最後",
    "全て", "すべて", "みんな", "皆", "他", "別", "同じ", "違う",
    "色々", "様々", "いろいろ", "さまざま", "等", "的",
    # Interview-specific generic words
    "質問", "回答", "意見", "考え", "お話", "説明", "ご説明",
    "インタビュー", "アンケート", "調査",
}


@dataclass
class ClusterResult:
    """Result of clustering."""
    cluster_id: int
    label: str
    responses: List[UserResponse]
    centroid: Optional[np.ndarray] = None
    keywords: List[str] = field(default_factory=list)
    
    @property
    def size(self) -> int:
        """Number of responses in cluster."""
        return len(self.responses)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (excluding numpy arrays)."""
        return {
            "cluster_id": self.cluster_id,
            "label": self.label,
            "size": self.size,
            "keywords": self.keywords,
            "sample_responses": [r.content[:200] for r in self.responses[:3]],
        }


class TopicClusterer:
    """Cluster responses by topic using embeddings and HDBSCAN."""
    
    def __init__(self, settings: Optional[Settings] = None):
        """Initialize clusterer.
        
        Args:
            settings: Application settings
        """
        self.settings = settings or get_settings()
        self._embedder = None
        self._embeddings_cache: Dict[str, np.ndarray] = {}
    
    @property
    def embedder(self):
        """Lazy load sentence transformer."""
        if self._embedder is None:
            from sentence_transformers import SentenceTransformer
            self._embedder = SentenceTransformer(self.settings.embedding_model)
        return self._embedder
    
    def get_embeddings(self, texts: List[str]) -> np.ndarray:
        """Get embeddings for texts.
        
        Args:
            texts: List of text strings
            
        Returns:
            Numpy array of embeddings
        """
        # Check cache for already computed embeddings
        uncached_indices = []
        uncached_texts = []
        
        for i, text in enumerate(texts):
            if text not in self._embeddings_cache:
                uncached_indices.append(i)
                uncached_texts.append(text)
        
        # Compute new embeddings
        if uncached_texts:
            new_embeddings = self.embedder.encode(
                uncached_texts,
                show_progress_bar=True,
                convert_to_numpy=True,
            )
            
            # Cache new embeddings
            for i, text in enumerate(uncached_texts):
                self._embeddings_cache[text] = new_embeddings[i]
        
        # Build result array
        embeddings = np.array([self._embeddings_cache[text] for text in texts])
        return embeddings
    
    def cluster_responses(
        self,
        responses: List[UserResponse],
        min_cluster_size: Optional[int] = None,
    ) -> List[ClusterResult]:
        """Cluster responses using HDBSCAN.
        
        Args:
            responses: List of user responses
            min_cluster_size: Minimum cluster size (overrides settings)
            
        Returns:
            List of ClusterResult objects
        """
        if len(responses) < 5:
            # Not enough responses to cluster
            return [ClusterResult(
                cluster_id=0,
                label="全回答",
                responses=responses,
                keywords=[],
            )]
        
        import hdbscan
        
        min_size = min_cluster_size or self.settings.clustering_min_samples
        
        # Get embeddings
        texts = [r.content for r in responses]
        embeddings = self.get_embeddings(texts)
        
        # Cluster with HDBSCAN
        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=min_size,
            min_samples=1,
            metric='euclidean',
            cluster_selection_method='eom',
        )
        
        labels = clusterer.fit_predict(embeddings)
        
        # Group responses by cluster
        clusters_dict: Dict[int, List[UserResponse]] = {}
        embeddings_dict: Dict[int, List[np.ndarray]] = {}
        
        for i, (resp, label) in enumerate(zip(responses, labels)):
            if label not in clusters_dict:
                clusters_dict[label] = []
                embeddings_dict[label] = []
            clusters_dict[label].append(resp)
            embeddings_dict[label].append(embeddings[i])
        
        # Build cluster results
        results = []
        for cluster_id in sorted(clusters_dict.keys()):
            cluster_responses = clusters_dict[cluster_id]
            cluster_embeddings = np.array(embeddings_dict[cluster_id])
            
            # Compute centroid
            centroid = cluster_embeddings.mean(axis=0)
            
            # Extract keywords using TF-IDF (with stopword filtering)
            keywords = self._extract_cluster_keywords(cluster_responses)
            
            # Generate meaningful label based on keywords
            label = self._generate_cluster_label(cluster_responses, keywords, cluster_id)
            
            results.append(ClusterResult(
                cluster_id=cluster_id,
                label=label,
                responses=cluster_responses,
                centroid=centroid,
                keywords=keywords,
            ))
        
        return results
    
    def _extract_cluster_keywords(
        self,
        responses: List[UserResponse],
        top_n: int = 5,
    ) -> List[str]:
        """Extract keywords from cluster using TF-IDF with stopword filtering.
        
        Args:
            responses: Responses in cluster
            top_n: Number of keywords to extract
            
        Returns:
            List of keyword strings (filtered for meaningful words)
        """
        if not responses:
            return []
        
        from sklearn.feature_extraction.text import TfidfVectorizer
        
        texts = [r.content for r in responses]
        
        try:
            vectorizer = TfidfVectorizer(
                max_features=200,
                token_pattern=r'(?u)\b\w\w+\b',
                max_df=0.8,
                min_df=2 if len(texts) > 10 else 1,
            )
            
            tfidf_matrix = vectorizer.fit_transform(texts)
            feature_names = vectorizer.get_feature_names_out()
            
            # Get average TF-IDF scores
            avg_scores = tfidf_matrix.mean(axis=0).A1
            
            # Get sorted indices by score
            sorted_indices = avg_scores.argsort()[::-1]
            
            # Filter out stopwords and collect top keywords
            keywords = []
            for idx in sorted_indices:
                word = feature_names[idx]
                # Skip stopwords, single characters, and numeric strings
                if (word not in JAPANESE_STOPWORDS and 
                    len(word) > 1 and 
                    not word.isdigit()):
                    keywords.append(word)
                    if len(keywords) >= top_n:
                        break
            
            return keywords
            
        except Exception:
            return []
    
    def _generate_cluster_label(
        self,
        responses: List[UserResponse],
        keywords: List[str],
        cluster_id: int,
    ) -> str:
        """Generate a meaningful label for a cluster based on its content.
        
        Args:
            responses: Responses in cluster
            keywords: Extracted keywords
            cluster_id: Cluster ID
            
        Returns:
            Human-readable cluster label
        """
        if cluster_id == -1:
            return "その他（未分類）"
        
        if not keywords:
            # Try to extract key phrases from sample responses
            sample_phrases = self._extract_key_phrases(responses[:5])
            if sample_phrases:
                return f"「{sample_phrases[0]}」"
            return f"クラスタ {cluster_id + 1}"
        
        # Use top 2 keywords to form a label (shorter is better for display)
        if len(keywords) >= 2:
            # Join top keywords with appropriate connector
            label_keywords = keywords[:2]
            label = f"「{'・'.join(label_keywords)}」"
        else:
            label = f"「{keywords[0]}」"
        
        return label
    
    def _extract_key_phrases(
        self,
        responses: List[UserResponse],
        max_length: int = 20,
    ) -> List[str]:
        """Extract key phrases from responses for labeling.
        
        Args:
            responses: Sample responses
            max_length: Maximum phrase length
            
        Returns:
            List of key phrases
        """
        import re
        
        # Additional phrases to filter (not stopwords, but not meaningful for labels)
        LABEL_STOPWORDS = {
            "ありがとう", "ありがとうございました", "ありがとうございます",
            "聞いてくれてありがとう", "こちらこそありがとう",
        }
        
        phrases = []
        for resp in responses:
            content = resp.content
            
            # Extract quoted phrases 「」or key patterns
            quoted = re.findall(r'「([^」]{3,20})」', content)
            if quoted:
                phrases.extend(quoted)
            
            # Extract noun phrases (simple heuristic: consecutive kanji/katakana)
            noun_patterns = re.findall(r'[一-龯ァ-ヴー]{3,15}', content)
            for np in noun_patterns:
                if (np not in JAPANESE_STOPWORDS and 
                    np not in LABEL_STOPWORDS and
                    len(np) <= max_length):
                    phrases.append(np)
        
        # Deduplicate while preserving order
        seen = set()
        unique_phrases = []
        for p in phrases:
            if (p not in seen and 
                p not in JAPANESE_STOPWORDS and
                p not in LABEL_STOPWORDS):
                seen.add(p)
                unique_phrases.append(p)
        
        # If all phrases were filtered, check if it's a "thank you" cluster
        if not unique_phrases:
            combined = ' '.join([r.content for r in responses])
            if 'ありがとう' in combined:
                return ["挨拶・お礼"]
        
        return unique_phrases[:3]
    
    def reduce_dimensions(
        self,
        embeddings: np.ndarray,
        n_components: int = 2,
    ) -> np.ndarray:
        """Reduce embedding dimensions for visualization.
        
        Args:
            embeddings: High-dimensional embeddings
            n_components: Target dimensions (2 or 3)
            
        Returns:
            Reduced dimension embeddings
        """
        import umap
        
        reducer = umap.UMAP(
            n_components=n_components,
            random_state=42,
            n_neighbors=min(15, len(embeddings) - 1),
            min_dist=0.1,
        )
        
        return reducer.fit_transform(embeddings)
    
    def get_cluster_summary(
        self,
        clusters: List[ClusterResult]
    ) -> Dict[str, Any]:
        """Get summary statistics for clusters.
        
        Args:
            clusters: List of cluster results
            
        Returns:
            Dictionary with summary statistics
        """
        total = sum(c.size for c in clusters)
        
        return {
            "total_responses": total,
            "num_clusters": len([c for c in clusters if c.cluster_id != -1]),
            "noise_count": sum(c.size for c in clusters if c.cluster_id == -1),
            "clusters": [c.to_dict() for c in clusters],
        }

