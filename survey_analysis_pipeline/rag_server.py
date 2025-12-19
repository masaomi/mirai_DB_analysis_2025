#!/usr/bin/env python3
"""
RAG Search API Server & Persona Assembly Backend

FastAPI server that provides:
1. RAG search endpoint for Next.js Q&A
2. Persona Assembly real-time discussion endpoints (SSE)

Usage:
    pixi run python rag_server.py --slug bill-of-lading --port 8001
"""

import json
import os
import sys
import asyncio
import uuid
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, AsyncGenerator

import typer
import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# ChromaDB
import chromadb
from chromadb.config import Settings

# LLM & Utilities
import litellm
from dotenv import load_dotenv

# Ensure we can import from local modules
sys.path.append(str(Path(__file__).parent))
from config.settings import get_settings

# Load environment variables
load_dotenv()

app_cli = typer.Typer()

# --- Data Models ---

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

# Persona Assembly Models
class PersonaConfig(BaseModel):
    id: str
    name: str
    description: str
    model: str
    system_prompt: str
    avatar: Optional[str] = None
    color: Optional[str] = None

class DiscussionSettings(BaseModel):
    personas: List[PersonaConfig]
    facilitator_id: str
    topic: str
    context: str = ""  # Report content or summary
    max_rounds: int = 10
    max_time_minutes: int = 30
    max_tokens: int = 50000

class InterruptRequest(BaseModel):
    session_id: str
    content: str
    user_name: str = "User"

class SessionResponse(BaseModel):
    session_id: str
    status: str

# --- Global State ---
_chroma_client: Optional[chromadb.PersistentClient] = None
_collection: Optional[chromadb.Collection] = None
_metadata: Optional[Dict[str, Any]] = None

# --- Persona Session Logic ---

class PersonaSession:
    def __init__(self, session_id: str, settings: DiscussionSettings):
        self.session_id = session_id
        self.settings = settings
        self.history: List[Dict[str, Any]] = []  # Chat history
        self.event_queue: asyncio.Queue = asyncio.Queue()
        self.is_active = True
        self.current_round = 0
        self.total_tokens = 0
        self.token_usage: Dict[str, int] = {p.id: 0 for p in settings.personas}
        self.interrupt_queue: asyncio.Queue = asyncio.Queue()
        self.start_time: Optional[float] = None  # Set when discussion starts
        self.final_report: Optional[str] = None  # Final summary report
        
        # System prompt construction with topic focus
        topic_instruction = f"""
【重要な指示】
- 議論のテーマ: 「{settings.topic}」
- 必ずこのテーマに関連した発言のみを行ってください
- テーマから逸脱した話題は避けてください
- 他の参加者の意見を尊重しつつ、建設的な議論を心がけてください
- 簡潔かつ的確な発言を心がけてください（長すぎる発言は避けてください）
"""
        self.system_prompts = {
            p.id: f"{p.system_prompt}\n\nあなたは「{p.name}」として発言してください。他の参加者やファシリテーターと議論し、合意形成を目指してください。{topic_instruction}"
            for p in settings.personas
        }
    
    def check_end_conditions(self) -> Optional[str]:
        """Check if any end condition is met. Returns reason or None."""
        # Check rounds
        if self.current_round >= self.settings.max_rounds:
            return "max_rounds_reached"
        
        # Check time
        if self.start_time:
            elapsed_minutes = (time.time() - self.start_time) / 60
            if elapsed_minutes >= self.settings.max_time_minutes:
                return "time_limit_reached"
        
        # Check tokens
        if self.total_tokens >= self.settings.max_tokens:
            return "token_limit_reached"
        
        return None

    async def add_event(self, event_type: str, data: Any):
        """Add event to SSE queue."""
        await self.event_queue.put({
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        })

    def get_persona(self, persona_id: str) -> Optional[PersonaConfig]:
        for p in self.settings.personas:
            if p.id == persona_id:
                return p
        return None

class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, PersonaSession] = {}

    def create_session(self, settings: DiscussionSettings) -> str:
        session_id = str(uuid.uuid4())
        session = PersonaSession(session_id, settings)
        self.sessions[session_id] = session
        return session_id

    def get_session(self, session_id: str) -> Optional[PersonaSession]:
        return self.sessions.get(session_id)

    async def stream_events(self, session_id: str) -> AsyncGenerator[str, None]:
        session = self.get_session(session_id)
        if not session:
            yield "data: {\"type\": \"error\", \"data\": \"Session not found\"}\n\n"
            return

        try:
            while session.is_active:
                # Wait for event with timeout to send keepalive
                try:
                    event = await asyncio.wait_for(session.event_queue.get(), timeout=15.0)
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"

# Global session manager
session_manager = SessionManager()

# --- Discussion Logic ---

def check_approaching_end(session: "PersonaSession") -> Optional[str]:
    """Check if discussion is approaching end conditions (80% threshold)."""
    # Check rounds (80% of max)
    if session.current_round >= session.settings.max_rounds * 0.8:
        remaining = session.settings.max_rounds - session.current_round
        return f"残り{remaining}ラウンドで終了します"
    
    # Check time (80% of max)
    if session.start_time:
        elapsed_minutes = (time.time() - session.start_time) / 60
        if elapsed_minutes >= session.settings.max_time_minutes * 0.8:
            remaining = round(session.settings.max_time_minutes - elapsed_minutes, 1)
            return f"残り約{remaining}分で終了します"
    
    # Check tokens (80% of max)
    if session.total_tokens >= session.settings.max_tokens * 0.8:
        remaining = session.settings.max_tokens - session.total_tokens
        return f"残り約{remaining}トークンで終了します"
    
    return None


async def generate_final_report(session: "PersonaSession", facilitator) -> None:
    """Generate final summary report by the facilitator."""
    await session.add_event("report_start", {
        "message": "ファシリテーターが議論のまとめレポートを作成しています..."
    })
    
    # Prepare report generation prompt
    report_prompt = f"""これまでの議論を踏まえて、以下の形式で最終レポートを作成してください：

## 議論テーマ
{session.settings.topic}

## 議論の要約
（これまでの議論の主要なポイントをまとめてください）

## 各立場からの意見
（各参加者の主な意見・主張を整理してください）

## 合意点
（参加者間で合意が得られた点をリストアップしてください）

## 相違点・課題
（意見が分かれた点や今後の課題をリストアップしてください）

## 結論・提言
（議論全体を踏まえた結論と、法案提出に向けた提言をまとめてください）

---
レポートは日本語で、Markdown形式で記述してください。"""
    
    # Build context from history
    history_summary = "\n".join([
        f"[{msg.get('name', 'ユーザー')}]: {msg['content'][:200]}..."
        if len(msg['content']) > 200 else f"[{msg.get('name', 'ユーザー')}]: {msg['content']}"
        for msg in session.history[-20:]  # Last 20 messages
        if msg["role"] != "system"
    ])
    
    messages = [
        {"role": "system", "content": f"あなたは議論のファシリテーター「{facilitator.name}」です。これまでの議論をまとめ、最終レポートを作成してください。"},
        {"role": "user", "content": f"これまでの議論内容:\n{history_summary}\n\n{report_prompt}"}
    ]
    
    try:
        model_name = facilitator.model
        api_key = None
        api_base = None
        
        if model_name.startswith("ollama/"):
            api_base = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        elif not model_name.startswith("openrouter/"):
            model_name = f"openrouter/{model_name}"
            api_key = os.environ.get("OPENROUTER_API_KEY")
        
        completion_kwargs = {
            "model": model_name,
            "messages": messages,
            "stream": True,
            "temperature": 0.5,  # Lower temperature for more coherent report
            "max_tokens": 2000,
        }
        
        if api_key:
            completion_kwargs["api_key"] = api_key
        if api_base:
            completion_kwargs["api_base"] = api_base
        
        await session.add_event("typing_start", {"persona_id": facilitator.id, "is_report": True})
        
        full_content = ""
        response = await litellm.acompletion(**completion_kwargs)
        
        async for chunk in response:
            delta = chunk.choices[0].delta.content
            if delta:
                full_content += delta
                await session.add_event("report_token", {
                    "persona_id": facilitator.id,
                    "content": delta
                })
        
        await session.add_event("report_end", {
            "persona_id": facilitator.id,
            "content": full_content,
            "name": facilitator.name
        })
        
        # Store report in session
        session.final_report = full_content
        
    except Exception as e:
        print(f"Report generation error: {e}")
        await session.add_event("report_error", {"error": str(e)})


async def run_discussion(session_id: str):
    """Background task to run the discussion loop."""
    session = session_manager.get_session(session_id)
    if not session:
        return

    try:
        # Initial event
        await session.add_event("start", {
            "topic": session.settings.topic,
            "personas": [p.dict() for p in session.settings.personas]
        })
        
        # RAG Search for Context
        rag_context = ""
        if _collection:
            try:
                # Query using the topic
                results = _collection.query(
                    query_texts=[session.settings.topic],
                    n_results=10,
                    include=["documents", "metadatas"]
                )
                
                documents = results.get("documents", [[]])[0]
                metadatas = results.get("metadatas", [[]])[0]
                
                if documents:
                    rag_context = "\n\n【関連するアンケート回答データ (RAG検索結果)】\n"
                    for i, (doc, meta) in enumerate(zip(documents, metadatas)):
                        rag_context += f"--- 回答 {i+1} ---\n{doc}\n"
                    
                    # Notify frontend
                    await session.add_event("rag_search", {
                        "count": len(documents),
                        "query": session.settings.topic
                    })
            except Exception as e:
                print(f"RAG search error: {e}")

        # Context initialization
        initial_context = f"議題: {session.settings.topic}\n\n背景情報:\n{session.settings.context}{rag_context}"
        session.history.append({"role": "system", "content": initial_context})

        facilitator = session.get_persona(session.settings.facilitator_id)
        if not facilitator:
            await session.add_event("error", "Facilitator not found")
            return

        # Set start time for time limit tracking
        session.start_time = time.time()

        # Track if final report has been generated
        final_report_generated = False
        
        # Discussion Loop
        while session.is_active:
            # Check end conditions
            end_reason = session.check_end_conditions()
            if end_reason:
                # Generate final report before ending
                if not final_report_generated:
                    await generate_final_report(session, facilitator)
                    final_report_generated = True
                await session.add_event("end", {"reason": end_reason})
                session.is_active = False
                break
            
            # Check if approaching end conditions (80% threshold)
            approaching_end = check_approaching_end(session)
            if approaching_end and not final_report_generated:
                await session.add_event("approaching_end", {"warning": approaching_end})
                # Start final report generation
                await generate_final_report(session, facilitator)
                final_report_generated = True
                # After report, continue one more round for any final comments
                continue

            session.current_round += 1
            await session.add_event("round_start", {
                "round": session.current_round,
                "total_tokens": session.total_tokens,
                "elapsed_minutes": round((time.time() - session.start_time) / 60, 1)
            })

            # Check for user interrupt
            if not session.interrupt_queue.empty():
                interrupt_content = await session.interrupt_queue.get()
                user_msg = {"role": "user", "content": interrupt_content}
                session.history.append(user_msg)
                await session.add_event("user_message", {"content": interrupt_content})
                
                # Let facilitator respond to interrupt
                await generate_persona_response(session, facilitator.id, is_interrupt_response=True)
                continue

            # Standard flow: Facilitator speaks first/last, others in between
            # Simple round robin for now, but facilitator guides it
            
            # Determine speaker order for this round
            # For simplicity: Facilitator -> Others -> Facilitator summary
            speakers = [facilitator.id] + [p.id for p in session.settings.personas if p.id != facilitator.id]
            
            for speaker_id in speakers:
                # Check end conditions before each speaker
                end_reason = session.check_end_conditions()
                if end_reason:
                    await session.add_event("end", {"reason": end_reason})
                    session.is_active = False
                    break

                # Check for interrupt before each speaker
                if not session.interrupt_queue.empty():
                    interrupt_content = await session.interrupt_queue.get()
                    user_msg = {"role": "user", "content": interrupt_content}
                    session.history.append(user_msg)
                    await session.add_event("user_message", {"content": interrupt_content})
                    # Break loop to handle interrupt immediately
                    # In next loop iteration, facilitator will respond
                    break
                
                await generate_persona_response(session, speaker_id)

    except Exception as e:
        print(f"Discussion error: {e}")
        await session.add_event("error", str(e))
        session.is_active = False

async def generate_persona_response(session: PersonaSession, persona_id: str, is_interrupt_response: bool = False):
    """Generate response for a specific persona using LLM."""
    persona = session.get_persona(persona_id)
    if not persona:
        return

    # Prepare messages
    # Filter history to keep context window manageable if needed
    messages = [{"role": "system", "content": session.system_prompts[persona_id]}]
    
    # Convert history to format expected by LLM
    # We map 'user' role to 'user' and persona responses to 'assistant' or 'user' with name prefix
    # For simplicity, we treat all previous messages as 'user' messages from the perspective of the current persona,
    # annotated with who spoke.
    
    formatted_history = []
    for msg in session.history:
        if msg["role"] == "system":
            continue
        
        role = "user" # Default to user
        content = msg["content"]
        
        if "name" in msg:
            content = f"[{msg['name']}の発言]: {content}"
        elif msg["role"] == "user":
            content = f"[ユーザーの発言]: {content}"
            
        formatted_history.append({"role": role, "content": content})
    
    messages.extend(formatted_history[-10:]) # Keep last 10 messages for context

    # Call LLM with streaming
    try:
        model_name = persona.model
        api_key = None
        api_base = None
        
        # Handle OpenRouter prefix - add openrouter/ prefix for non-ollama models
        if model_name.startswith("ollama/"):
            # Local Ollama - no prefix needed, use localhost
            api_base = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        elif not model_name.startswith("openrouter/"):
            # Add openrouter prefix for cloud models (anthropic/, openai/, google/, etc.)
            model_name = f"openrouter/{model_name}"
            api_key = os.environ.get("OPENROUTER_API_KEY")
        
        # Start streaming event
        await session.add_event("typing_start", {"persona_id": persona.id})
        
        full_content = ""

        # Using litellm for unified interface with OpenRouter or Ollama
        completion_kwargs = {
            "model": model_name,
            "messages": messages,
            "stream": True,
            "temperature": 0.7,
            "max_tokens": 1000,
        }
        
        if api_key:
            completion_kwargs["api_key"] = api_key
        if api_base:
            completion_kwargs["api_base"] = api_base

        response = await litellm.acompletion(**completion_kwargs)
        
        async for chunk in response:
            delta = chunk.choices[0].delta.content
            if delta:
                full_content += delta
                await session.add_event("token", {
                    "persona_id": persona.id, 
                    "content": delta
                })
        
        # Finished
        # Estimate tokens (roughly 1 token per 4 characters for Japanese)
        estimated_tokens = len(full_content) // 2 + len(str(messages)) // 4
        
        await session.add_event("typing_end", {
            "persona_id": persona.id, 
            "content": full_content,
            "tokens": estimated_tokens
        })
        
        # Update token tracking
        session.total_tokens += estimated_tokens
        session.token_usage[persona.id] = session.token_usage.get(persona.id, 0) + estimated_tokens
        
        # Update history
        session.history.append({
            "role": "assistant",
            "name": persona.name,
            "persona_id": persona.id,
            "content": full_content
        })
        
        # Update usage stats
        # Litellm stream doesn't always give usage, so we estimate or ignore for now
        # In production we'd count tokens properly
        
    except Exception as e:
        print(f"LLM Error ({persona.name}): {e}")
        error_msg = f"(エラーが発生しました: {str(e)})"
        await session.add_event("token", {"persona_id": persona.id, "content": error_msg})
        await session.add_event("typing_end", {"persona_id": persona.id, "content": error_msg})


# --- FastAPI App ---

def create_app(index_dir: Path) -> FastAPI:
    """Create FastAPI app with ChromaDB initialized."""
    global _chroma_client, _collection, _metadata
    
    # Load metadata if exists (RAG mode)
    metadata_path = index_dir / "metadata.json"
    if metadata_path.exists():
        with open(metadata_path, 'r', encoding='utf-8') as f:
            _metadata = json.load(f)
        collection_name = _metadata.get("collection_name", "survey_data")
        _chroma_client = chromadb.PersistentClient(path=str(index_dir))
        _collection = _chroma_client.get_collection(name=collection_name)
    
    # Create FastAPI app
    api = FastAPI(
        title="RAG Search & Persona API",
        description="API for survey Q&A and Persona Assembly",
        version="1.0.0",
    )
    
    # CORS for Next.js
    api.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:3002", "*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @api.get("/health")
    async def health():
        return {
            "status": "ok",
            "documents": _collection.count() if _collection else 0,
            "active_sessions": len(session_manager.sessions)
        }
    
    # --- RAG Endpoints ---
    
    @api.post("/query", response_model=QueryResponse)
    async def query(request: QueryRequest):
        if not _collection:
            raise HTTPException(status_code=500, detail="Collection not initialized")
        
        try:
            results = _collection.query(
                query_texts=[request.query],
                n_results=request.n_results,
                include=["documents", "metadatas", "distances"],
            )
            
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
                collection_name=_metadata.get("collection_name", "") if _metadata else "",
                total_documents=_collection.count(),
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # --- Persona Assembly Endpoints ---

    @api.post("/persona/start", response_model=SessionResponse)
    async def start_persona_session(settings: DiscussionSettings, background_tasks: BackgroundTasks):
        """Start a new persona discussion session."""
        try:
            session_id = session_manager.create_session(settings)
            
            # Start discussion in background
            background_tasks.add_task(run_discussion, session_id)
            
            return SessionResponse(session_id=session_id, status="started")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @api.get("/persona/stream")
    async def stream_persona_session(session_id: str):
        """Stream discussion events using SSE."""
        return StreamingResponse(
            session_manager.stream_events(session_id),
            media_type="text/event-stream"
        )

    @api.post("/persona/interrupt")
    async def interrupt_session(request: InterruptRequest):
        """Inject a user message into the discussion."""
        session = session_manager.get_session(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        await session.interrupt_queue.put(request.content)
        return {"status": "interrupted"}

    @api.post("/persona/save")
    async def save_session_log(session_id: str = ""): # TODO: Implement saving logic
        # Implementation for saving logs
        return {"status": "saved"}

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
        # Default path relative to this script or current dir
        output_dir = Path("outputs") / slug
    
    index_dir = output_dir / "vector_index"
    
    # Warn but don't fail if index doesn't exist (allow Persona-only mode)
    if not index_dir.exists():
        console.print(f"[yellow]Index not found at: {index_dir}[/yellow]")
        console.print("[yellow]RAG features will be disabled. Persona Assembly still available.[/yellow]")
    
    # Create app
    api = create_app(index_dir)
    
    console.print(Panel(
        f"[bold blue]RAG & Persona API Server[/bold blue]\n"
        f"Survey: {slug}\n"
        f"URL: http://{host}:{port}\n"
        f"\n"
        f"[dim]Endpoints:[/dim]\n"
        f"  GET  /health          - Check status\n"
        f"  POST /query           - RAG Search\n"
        f"  POST /persona/start   - Start Discussion\n"
        f"  GET  /persona/stream  - SSE Stream\n",
        title="Server Running",
    ))
    
    # Run server
    uvicorn.run(api, host=host, port=port, log_level="info")


if __name__ == "__main__":
    app_cli()

