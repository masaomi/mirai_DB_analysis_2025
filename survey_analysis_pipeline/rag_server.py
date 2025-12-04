#!/usr/bin/env python3
"""
RAG Search API Server

FastAPI server that provides RAG search endpoint for Next.js Q&A.
Wraps ChromaDB with text query support (embedding computation included).

Usage:
    pixi run python rag_server.py --slug bill-of-lading --port 8001
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any

import typer
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ChromaDB
import chromadb
from chromadb.config import Settings

app_cli = typer.Typer()


class QueryRequest(BaseModel):
    query: str
    n_results: int = 10


class QueryResult(BaseModel):
    id: str
    content: str
    metadata: Dict[str, Any]
    distance: float


class QueryResponse(BaseModel):
    results: List[QueryResult]
    collection_name: str
    total_documents: int


# Global state
_chroma_client: Optional[chromadb.PersistentClient] = None
_collection: Optional[chromadb.Collection] = None
_metadata: Optional[Dict[str, Any]] = None


def create_app(index_dir: Path) -> FastAPI:
    """Create FastAPI app with ChromaDB initialized."""
    global _chroma_client, _collection, _metadata
    
    # Load metadata
    metadata_path = index_dir / "metadata.json"
    if not metadata_path.exists():
        raise ValueError(f"Metadata not found: {metadata_path}")
    
    with open(metadata_path, 'r', encoding='utf-8') as f:
        _metadata = json.load(f)
    
    collection_name = _metadata.get("collection_name", "survey_data")
    
    # Initialize ChromaDB
    _chroma_client = chromadb.PersistentClient(path=str(index_dir))
    _collection = _chroma_client.get_collection(name=collection_name)
    
    # Create FastAPI app
    api = FastAPI(
        title="RAG Search API",
        description="RAG search endpoint for survey Q&A",
        version="1.0.0",
    )
    
    # CORS for Next.js
    api.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:3002"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @api.get("/health")
    async def health():
        return {
            "status": "ok",
            "collection": collection_name,
            "documents": _collection.count() if _collection else 0,
        }
    
    @api.get("/metadata")
    async def get_metadata():
        return _metadata
    
    @api.post("/query", response_model=QueryResponse)
    async def query(request: QueryRequest):
        if not _collection:
            raise HTTPException(status_code=500, detail="Collection not initialized")
        
        try:
            # Query ChromaDB (embedding computed automatically)
            results = _collection.query(
                query_texts=[request.query],
                n_results=request.n_results,
                include=["documents", "metadatas", "distances"],
            )
            
            # Format results
            formatted_results: List[QueryResult] = []
            
            ids = results.get("ids", [[]])[0]
            documents = results.get("documents", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0]
            
            for i in range(len(ids)):
                formatted_results.append(QueryResult(
                    id=ids[i],
                    content=documents[i] if documents else "",
                    metadata=metadatas[i] if metadatas else {},
                    distance=distances[i] if distances else 0.0,
                ))
            
            return QueryResponse(
                results=formatted_results,
                collection_name=collection_name,
                total_documents=_collection.count(),
            )
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    return api


@app_cli.command()
def serve(
    slug: str = typer.Argument(..., help="Survey slug"),
    port: int = typer.Option(8001, "--port", "-p", help="Port to serve on"),
    host: str = typer.Option("localhost", "--host", "-h", help="Host to bind to"),
    output_dir: Optional[Path] = typer.Option(None, "--output", "-o", help="Output directory"),
):
    """Start RAG search API server."""
    from rich.console import Console
    from rich.panel import Panel
    
    console = Console()
    
    if output_dir is None:
        output_dir = Path("outputs") / slug
    
    index_dir = output_dir / "vector_index"
    
    if not index_dir.exists():
        console.print(f"[red]Index not found: {index_dir}[/red]")
        console.print("Run 'build-index' first.")
        raise typer.Exit(1)
    
    # Create app
    api = create_app(index_dir)
    
    console.print(Panel(
        f"[bold blue]RAG Search API Server[/bold blue]\n"
        f"Survey: {slug}\n"
        f"Collection: {_metadata.get('collection_name', 'unknown')}\n"
        f"Documents: {_collection.count() if _collection else 0}\n"
        f"URL: http://{host}:{port}\n"
        f"\n"
        f"[dim]Endpoints:[/dim]\n"
        f"  GET  /health   - Health check\n"
        f"  GET  /metadata - Collection metadata\n"
        f"  POST /query    - Search (body: {{query, n_results}})",
        title="RAG Server",
    ))
    
    console.print(f"\n[yellow]Press Ctrl+C to stop[/yellow]\n")
    
    # Run server
    uvicorn.run(api, host=host, port=port, log_level="info")


if __name__ == "__main__":
    app_cli()


