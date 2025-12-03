"""Cluster responses by topic using embeddings."""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import numpy as np

from pipeline.extractors.response_extractor import UserResponse
from config.settings import Settings, get_settings


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
            
            # Generate label
            if cluster_id == -1:
                label = "その他（未分類）"
            else:
                label = f"クラスタ {cluster_id + 1}"
            
            # Extract keywords using TF-IDF
            keywords = self._extract_cluster_keywords(cluster_responses)
            
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
        """Extract keywords from cluster using TF-IDF.
        
        Args:
            responses: Responses in cluster
            top_n: Number of keywords to extract
            
        Returns:
            List of keyword strings
        """
        if not responses:
            return []
        
        from sklearn.feature_extraction.text import TfidfVectorizer
        
        texts = [r.content for r in responses]
        
        try:
            vectorizer = TfidfVectorizer(
                max_features=100,
                token_pattern=r'(?u)\b\w\w+\b',
                max_df=0.8,
                min_df=1,
            )
            
            tfidf_matrix = vectorizer.fit_transform(texts)
            feature_names = vectorizer.get_feature_names_out()
            
            # Get average TF-IDF scores
            avg_scores = tfidf_matrix.mean(axis=0).A1
            
            # Get top keywords
            top_indices = avg_scores.argsort()[-top_n:][::-1]
            keywords = [feature_names[i] for i in top_indices]
            
            return keywords
            
        except Exception:
            return []
    
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

