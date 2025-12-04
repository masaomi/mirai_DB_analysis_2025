"""Build vector index for RAG-based Q&A."""

from pathlib import Path
from typing import List, Dict, Any, Optional
import json

from config.settings import Settings, get_settings
from pipeline.extractors.response_extractor import UserResponse


class IndexBuilder:
    """Build ChromaDB index for RAG Q&A."""
    
    def __init__(self, settings: Optional[Settings] = None):
        """Initialize index builder.
        
        Args:
            settings: Application settings
        """
        self.settings = settings or get_settings()
        self._client = None
        self._embedding_function = None
    
    @property
    def client(self):
        """Lazy load ChromaDB client."""
        if self._client is None:
            import chromadb
            self._client = chromadb.Client()
        return self._client
    
    @property
    def embedding_function(self):
        """Lazy load embedding function."""
        if self._embedding_function is None:
            from chromadb.utils import embedding_functions
            self._embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=self.settings.embedding_model
            )
        return self._embedding_function
    
    def build_index(
        self,
        survey_slug: str,
        responses: List[UserResponse],
        report_content: str,
        cluster_summaries: List[Dict[str, Any]],
        output_dir: Path,
    ) -> Path:
        """Build vector index from survey data.
        
        Args:
            survey_slug: Survey identifier
            responses: List of user responses
            report_content: Generated report markdown
            cluster_summaries: Cluster summary data
            output_dir: Output directory
            
        Returns:
            Path to index directory
        """
        import chromadb
        from chromadb.config import Settings as ChromaSettings
        
        # Create persistent client
        index_dir = output_dir / "vector_index"
        index_dir.mkdir(parents=True, exist_ok=True)
        
        client = chromadb.PersistentClient(
            path=str(index_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        
        # Create or get collection
        collection_name = f"survey_{survey_slug}"
        
        # Delete existing collection if exists
        try:
            client.delete_collection(collection_name)
        except Exception:
            pass
        
        collection = client.create_collection(
            name=collection_name,
            embedding_function=self.embedding_function,
            metadata={"survey_slug": survey_slug},
        )
        
        # Index responses
        self._index_responses(collection, responses)
        
        # Index report sections
        self._index_report(collection, report_content)
        
        # Index cluster summaries
        self._index_clusters(collection, cluster_summaries)
        
        # Save metadata
        metadata = {
            "survey_slug": survey_slug,
            "response_count": len(responses),
            "cluster_count": len(cluster_summaries),
            "collection_name": collection_name,
        }
        
        metadata_path = index_dir / "metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        return index_dir
    
    def _index_responses(
        self,
        collection,
        responses: List[UserResponse],
    ) -> None:
        """Index user responses.
        
        Args:
            collection: ChromaDB collection
            responses: List of responses
        """
        if not responses:
            return
        
        # Batch index
        batch_size = 100
        for i in range(0, len(responses), batch_size):
            batch = responses[i:i + batch_size]
            
            ids = [f"response_{i + j}" for j in range(len(batch))]
            documents = [r.content for r in batch]
            metadatas = [
                {
                    "type": "response",
                    "session_id": r.session_id,
                    "question": r.preceding_question[:200] if r.preceding_question else "",
                }
                for r in batch
            ]
            
            collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
            )
    
    def _index_report(
        self,
        collection,
        report_content: str,
    ) -> None:
        """Index report sections.
        
        Args:
            collection: ChromaDB collection
            report_content: Report markdown content
        """
        # Split report into sections
        sections = []
        current_section = ""
        current_title = "Introduction"
        
        for line in report_content.split('\n'):
            if line.startswith('## '):
                if current_section:
                    sections.append({
                        "title": current_title,
                        "content": current_section.strip(),
                    })
                current_title = line[3:].strip()
                current_section = ""
            else:
                current_section += line + "\n"
        
        # Add last section
        if current_section:
            sections.append({
                "title": current_title,
                "content": current_section.strip(),
            })
        
        # Index sections
        for i, section in enumerate(sections):
            if len(section['content']) > 50:  # Skip very short sections
                collection.add(
                    ids=[f"report_section_{i}"],
                    documents=[section['content']],
                    metadatas=[{
                        "type": "report_section",
                        "title": section['title'],
                    }],
                )
    
    def _index_clusters(
        self,
        collection,
        cluster_summaries: List[Dict[str, Any]],
    ) -> None:
        """Index cluster summaries.
        
        Args:
            collection: ChromaDB collection
            cluster_summaries: Cluster summary data
        """
        for i, cluster in enumerate(cluster_summaries):
            # Create searchable document from cluster
            document = f"""
クラスタ: {cluster.get('cluster_label', '')}
主張: {cluster.get('group_assertion', '')}
論点: {', '.join(cluster.get('main_points', []))}
感情傾向: {cluster.get('overall_sentiment', '')}
特徴: {', '.join(cluster.get('distinguishing_features', []))}
""".strip()
            
            # Convert numpy types to Python native types for ChromaDB compatibility
            cluster_id = cluster.get('cluster_id', i)
            if hasattr(cluster_id, 'item'):  # numpy type
                cluster_id = cluster_id.item()
            
            response_count = cluster.get('response_count', 0)
            if hasattr(response_count, 'item'):  # numpy type
                response_count = response_count.item()
            
            collection.add(
                ids=[f"cluster_{i}"],
                documents=[document],
                metadatas=[{
                    "type": "cluster_summary",
                    "cluster_id": int(cluster_id),
                    "cluster_label": str(cluster.get('cluster_label', '')),
                    "response_count": int(response_count),
                }],
            )
    
    def query_index(
        self,
        index_dir: Path,
        query: str,
        n_results: int = 5,
        filter_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Query the vector index.
        
        Args:
            index_dir: Path to index directory
            query: Search query
            n_results: Number of results to return
            filter_type: Optional filter by document type
            
        Returns:
            List of matching documents with metadata
        """
        import chromadb
        from chromadb.config import Settings as ChromaSettings
        
        # Load metadata
        metadata_path = index_dir / "metadata.json"
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        # Connect to index
        client = chromadb.PersistentClient(
            path=str(index_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        
        collection = client.get_collection(
            name=metadata['collection_name'],
            embedding_function=self.embedding_function,
        )
        
        # Build query filter
        where = None
        if filter_type:
            where = {"type": filter_type}
        
        # Query
        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where,
        )
        
        # Format results
        documents = []
        for i in range(len(results['ids'][0])):
            documents.append({
                "id": results['ids'][0][i],
                "content": results['documents'][0][i],
                "metadata": results['metadatas'][0][i],
                "distance": results['distances'][0][i] if results['distances'] else None,
            })
        
        return documents

