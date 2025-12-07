#!/usr/bin/env python3
"""Survey Analysis Pipeline - CLI Application."""

import asyncio
import sys
from pathlib import Path
from typing import Optional, List
from datetime import datetime

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.panel import Panel

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import Settings, get_settings, LLMProvider
from core.llm_client import LLMClient
from pipeline.extractors.data_loader import SurveyDataLoader
from pipeline.extractors.response_extractor import ResponseExtractor
from pipeline.extractors.ronten_loader import RontenLoader
from pipeline.filters.cluster_filter import ClusterBasedFilter
from pipeline.analyzers.stance_detector import StanceDetector
from pipeline.analyzers.topic_clusterer import TopicClusterer
from pipeline.analyzers.minority_detector import MinorityDetector
from pipeline.analyzers.ronten_matcher import RontenMatcher
from pipeline.summarizers.cluster_summarizer import ClusterSummarizer
from pipeline.analyzers.quality_scorer import QualityScorer
from pipeline.summarizers.overall_summarizer import OverallSummarizer, RontenSummary, NovelInsight
from pipeline.generators.report_generator import ReportGenerator, ReportData
from pipeline.generators.chart_generator import ChartGenerator
from pipeline.generators.index_builder import IndexBuilder
from orchestration.multi_llm import MultiLLMOrchestrator, save_multi_llm_outputs
from orchestration.persona_assembly import PersonaAssembly


app = typer.Typer(
    name="survey-analyze",
    help="Survey Analysis Pipeline - Analyze survey responses and generate reports",
    add_completion=False,
)
console = Console()


def get_settings_with_provider(provider: Optional[str]) -> Settings:
    """Get settings with optional provider override."""
    settings = get_settings()
    if provider:
        try:
            settings.llm_provider = LLMProvider(provider)
        except ValueError:
            console.print(f"[red]Invalid provider: {provider}[/red]")
            console.print(f"Valid options: {', '.join([p.value for p in LLMProvider])}")
            raise typer.Exit(1)
    return settings


@app.command()
def list_surveys():
    """List available surveys in the data directory."""
    settings = get_settings()
    loader = SurveyDataLoader(settings)
    
    surveys = loader.get_available_surveys()
    
    if not surveys:
        console.print("[yellow]No surveys found in data directory.[/yellow]")
        console.print(f"Data directory: {settings.data_dir}")
        raise typer.Exit(0)
    
    table = Table(title="Available Surveys")
    table.add_column("Slug", style="cyan")
    table.add_column("Title", style="green")
    table.add_column("Sessions", justify="right")
    table.add_column("Completed", justify="right")
    table.add_column("Messages", justify="right")
    
    for slug in surveys:
        try:
            metadata = loader.get_survey_metadata(slug)
            table.add_row(
                slug,
                metadata.title[:40] + "..." if len(metadata.title) > 40 else metadata.title,
                str(metadata.total_sessions),
                str(metadata.completed_sessions),
                str(metadata.total_messages),
            )
        except Exception as e:
            table.add_row(slug, f"[red]Error: {e}[/red]", "-", "-", "-")
    
    console.print(table)


@app.command()
def analyze(
    survey_slug: str = typer.Argument(..., help="Survey slug to analyze"),
    output_dir: Optional[Path] = typer.Option(
        None, "--output", "-o",
        help="Output directory for reports"
    ),
    provider: Optional[str] = typer.Option(
        None, "--provider", "-p",
        help="LLM provider (ollama, bedrock, openrouter)"
    ),
    multi_llm: bool = typer.Option(
        False, "--multi-llm", "-m",
        help="Enable multi-LLM orchestration"
    ),
    persona: bool = typer.Option(
        False, "--persona", "-P",
        help="Enable persona assembly analysis"
    ),
    skip_summarization: bool = typer.Option(
        False, "--skip-summarization",
        help="Skip LLM summarization (analysis only)"
    ),
    skip_charts: bool = typer.Option(
        False, "--skip-charts",
        help="Skip chart generation"
    ),
    skip_index: bool = typer.Option(
        False, "--skip-index",
        help="Skip RAG index building"
    ),
):
    """Analyze a survey and generate report."""
    settings = get_settings_with_provider(provider)
    
    # Setup output directory
    if output_dir is None:
        output_dir = Path(settings.output_dir) / survey_slug
    output_dir.mkdir(parents=True, exist_ok=True)
    
    console.print(Panel(
        f"[bold blue]Analyzing Survey: {survey_slug}[/bold blue]\n"
        f"Provider: {settings.llm_provider.value}\n"
        f"Multi-LLM: {'Enabled' if multi_llm else 'Disabled'}\n"
        f"Persona: {'Enabled' if persona else 'Disabled'}",
        title="Survey Analysis Pipeline",
    ))
    
    # Run pipeline
    asyncio.run(_run_pipeline(
        survey_slug=survey_slug,
        output_dir=output_dir,
        settings=settings,
        multi_llm=multi_llm,
        persona=persona,
        skip_summarization=skip_summarization,
        skip_charts=skip_charts,
        skip_index=skip_index,
    ))


async def _run_pipeline(
    survey_slug: str,
    output_dir: Path,
    settings: Settings,
    multi_llm: bool,
    persona: bool,
    skip_summarization: bool,
    skip_charts: bool,
    skip_index: bool,
):
    """Run the analysis pipeline."""
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        
        # Phase 1: Extract data
        task = progress.add_task("[cyan]Extracting responses...", total=None)
        extractor = ResponseExtractor(settings)
        extraction_result = extractor.extract_responses(survey_slug)
        progress.update(task, completed=True)
        
        console.print(f"  ✓ Extracted {extraction_result.response_count} responses")
        
        # Phase 1.2: Load Ronten Context (if available)
        ronten_loader = RontenLoader(settings)
        ronten_context = ronten_loader.load_ronten_content(survey_slug)
        if ronten_context:
            console.print(f"  ✓ Loaded ronten context ({len(ronten_context)} chars)")
        else:
            console.print(f"  - No specific ronten context found for {survey_slug}")
        
        # Phase 2: Cluster first (embedding-based, no LLM needed)
        task = progress.add_task("[cyan]Clustering responses...", total=None)
        clusterer = TopicClusterer(settings)
        clusters_all = clusterer.cluster_responses(extraction_result.responses)
        progress.update(task, completed=True)
        
        console.print(f"  ✓ Found {len(clusters_all)} clusters")
        
        # Phase 2.5: Filter clusters (much fewer LLM calls than per-response)
        filter_stats = None
        filter_results = []
        
        if settings.relevance_filter_enabled:
            task = progress.add_task("[cyan]Filtering clusters by relevance...", total=None)
            llm_client = LLMClient(settings)
            cluster_filter = ClusterBasedFilter(settings, llm_client)
            
            clusters, filter_results, filter_stats = await cluster_filter.filter_clusters(
                clusters_all,
                extraction_result.survey_title,
                ronten_context=ronten_context,
            )
            progress.update(task, completed=True)
            
            # Display stats
            console.print(Panel(
                f"[bold]Cluster Filter Stats[/bold]\n"
                f"Total Clusters: {filter_stats.total_clusters}\n"
                f"Auto-included (≥{settings.min_cluster_size_for_report}): {filter_stats.auto_included_clusters}\n"
                f"LLM-checked: {filter_stats.llm_checked_clusters}\n"
                f"Excluded: {filter_stats.excluded_clusters}\n"
                f"Noise responses: {filter_stats.noise_responses}\n\n"
                f"[bold]Efficiency:[/bold]\n"
                f"LLM calls made: {filter_stats.llm_calls_made}\n"
                f"LLM calls saved: {filter_stats.llm_calls_saved} (vs per-response)\n"
                f"Final responses: {filter_stats.final_responses} / {filter_stats.total_responses}",
                title="Cluster-Based Filter",
                border_style="yellow"
            ))
            
            # Save filter results
            import json
            filter_log_path = output_dir / "cluster_filter_log.json"
            with open(filter_log_path, 'w', encoding='utf-8') as f:
                json.dump(
                    {
                        "stats": filter_stats.to_dict(),
                        "results": [r.to_dict() for r in filter_results]
                    },
                    f,
                    ensure_ascii=False,
                    indent=2
                )
        else:
            # No filtering - use all clusters above min size
            clusters = [c for c in clusters_all if c.size >= settings.min_cluster_size_for_report]
        
        console.print(f"  ✓ Using {len(clusters)} clusters for analysis")
        
        # Get filtered responses from included clusters
        filtered_responses = []
        for cluster in clusters:
            filtered_responses.extend(cluster.responses)
        
        # Phase 3: Analyze
        task = progress.add_task("[cyan]Detecting stances...", total=None)
        stance_detector = StanceDetector()
        stance_results = stance_detector.analyze_responses(filtered_responses)
        stance_distribution = stance_detector.get_stance_distribution(stance_results)
        progress.update(task, completed=True)
        
        task = progress.add_task("[cyan]Detecting minority opinions...", total=None)
        minority_detector = MinorityDetector(settings)
        # Detect minorities from ALL responses (including noise cluster)
        # Use min_score from settings (default 0.5 = 5/10 scale)
        minorities = minority_detector.detect_minorities(
            extraction_result.responses,
            min_score=settings.minority_min_score,
        )
        progress.update(task, completed=True)
        
        console.print(f"  ✓ Found {len(minorities)} minority opinions")
        
        # Phase 3: Summarize with LLM
        cluster_summaries = []
        overall_summary = None
        multi_llm_result = None
        
        if not skip_summarization:
            llm_client = LLMClient(settings)
            
            # Filter minority opinions by relevance if enabled
            if settings.minority_relevance_check and minorities:
                task = progress.add_task("[cyan]Filtering minority opinions by relevance...", total=None)
                minorities_before = len(minorities)
                minorities = await minority_detector.filter_by_relevance(
                    minorities,
                    extraction_result.survey_title,
                    llm_client,
                )
                progress.update(task, completed=True)
                console.print(f"  ✓ Filtered minorities: {minorities_before} → {len(minorities)} (relevant only)")
            
            task = progress.add_task("[cyan]Summarizing clusters...", total=None)
            cluster_summarizer = ClusterSummarizer(settings, llm_client)
            cluster_summaries = await cluster_summarizer.summarize_all_clusters(clusters)
            progress.update(task, completed=True)
            
            # Quality Scoring
            if settings.quality_scoring_enabled:
                task = progress.add_task("[cyan]Scoring cluster quality...", total=None)
                scorer = QualityScorer(settings, llm_client)
                cluster_summaries = await scorer.score_all_clusters(cluster_summaries)
                progress.update(task, completed=True)
                console.print(f"  ✓ Scored {len(cluster_summaries)} clusters")
            
            # Ronten-based analysis
            ronten_summaries = []
            novel_insights = []
            ronten_items = ronten_loader.get_ronten_items(survey_slug)
            
            if ronten_items:
                task = progress.add_task("[cyan]Matching opinions to legislative discussion points...", total=None)
                ronten_matcher = RontenMatcher(settings, llm_client)
                
                # Prepare opinions from cluster summaries for ronten matching
                opinions_for_matching = []
                for cs in cluster_summaries:
                    # Use cluster assertion and main points as representative opinion
                    content = f"{cs.group_assertion}. {'. '.join(cs.main_points)}"
                    if cs.representative_quote:
                        content += f" 代表的意見: {cs.representative_quote}"
                    opinions_for_matching.append({
                        "content": content,
                        "cluster_id": cs.cluster_id,
                        "cluster_label": cs.cluster_label,
                        "response_count": cs.response_count,
                        "session_ids": getattr(cs, 'representative_session_ids', []),
                    })
                
                # Add minority opinions
                for mo in minorities:
                    opinions_for_matching.append({
                        "content": mo.content,
                        "session_id": mo.session_id,
                        "is_minority": True,
                    })
                
                # Match to ronten
                ronten_analyses, novel_opinions = await ronten_matcher.analyze_by_ronten(
                    opinions_for_matching,
                    survey_slug,
                )
                
                progress.update(task, completed=True)
                console.print(f"  ✓ Matched opinions to {len(ronten_analyses)} discussion points")
                if novel_opinions:
                    console.print(f"  ✓ Found {len(novel_opinions)} novel insights not in legislative discussion")
                
                # Generate ronten summaries using LLM
                task = progress.add_task("[cyan]Generating ronten-based summaries...", total=None)
                
                for analysis in ronten_analyses:
                    # Collect all opinions for this ronten
                    all_opinions = (
                        analysis.supporting_opinions +
                        analysis.concerns +
                        analysis.expert_opinions +
                        analysis.general_opinions
                    )
                    
                    # Generate summary for this ronten
                    if all_opinions:
                        opinions_text = "\n".join(
                            f"- {op.get('content', '')[:200]}"
                            for op in all_opinions[:10]
                        )
                        
                        summary_prompt = f"""以下は「{analysis.ronten_title}」（法制審議会論点）に関連する意見です。
この論点について、意見を簡潔に要約してください（3-4文）。

## 関連意見
{opinions_text}

## 指示
- サポート意見、懸念、専門家の指摘を区別してください
- 具体的な内容を優先してください
- 100字程度で要約してください
"""
                        try:
                            summary_response = await llm_client.generate(summary_prompt)
                            summary_text = summary_response[:300]
                        except Exception:
                            summary_text = f"{analysis.opinion_count}件の関連意見があります。"
                        
                        # Collect session IDs from opinions
                        session_ids = []
                        for op in all_opinions:
                            # From cluster opinions
                            if op.get("session_ids"):
                                session_ids.extend(op.get("session_ids", []))
                            # From minority opinions
                            if op.get("session_id"):
                                session_ids.append(op.get("session_id"))
                        # Deduplicate and limit
                        unique_session_ids = list(dict.fromkeys(session_ids))[:5]
                        
                        ronten_summaries.append(RontenSummary(
                            ronten_id=analysis.ronten_id,
                            ronten_title=analysis.ronten_title,
                            opinion_count=analysis.opinion_count,
                            summary=summary_text,
                            supporting_points=[
                                op.get("content", "")[:150] for op in analysis.supporting_opinions[:3]
                            ],
                            concern_points=[
                                op.get("content", "")[:150] for op in analysis.concerns[:3]
                            ],
                            expert_points=[
                                op.get("content", "")[:150] for op in analysis.expert_opinions[:3]
                            ],
                            representative_quotes=[
                                op.get("content", "")[:200] for op in all_opinions[:2]
                            ],
                            representative_session_ids=unique_session_ids,
                        ))
                
                # Create novel insights
                for op in novel_opinions[:5]:  # Limit to top 5
                    match_data = op.get("ronten_match", {})
                    novel_insights.append(NovelInsight(
                        content=op.get("content", ""),
                        session_id=op.get("session_id", ""),
                        insight_type=match_data.get("insight_type", "general"),
                        summary=match_data.get("summary", "新規論点"),
                    ))
                
                progress.update(task, completed=True)
            
            # Generate overall summary
            overall_summarizer = OverallSummarizer(settings, llm_client)
            
            if multi_llm:
                # Use Multi-LLM consensus for overall summary
                task = progress.add_task("[cyan]Generating overall summary (Multi-LLM)...", total=None)
                orchestrator = MultiLLMOrchestrator(settings)
                
                overall_summary, multi_llm_result = await overall_summarizer.generate_summary_multi_llm(
                    orchestrator=orchestrator,
                survey_title=extraction_result.survey_title,
                total_responses=extraction_result.response_count,
                date_range=extraction_result.date_range,
                stance_distribution=stance_distribution,
                cluster_summaries=cluster_summaries,
                minority_opinions=minorities,
                    ronten_context=ronten_context,
                )
                
                # Save Multi-LLM outputs
                output_files = save_multi_llm_outputs(
                    multi_llm_result,
                    output_dir,
                    extraction_result.survey_title
                )
                
                progress.update(task, completed=True)
                console.print(f"  ✓ Multi-LLM agreement score: {multi_llm_result.agreement_score:.2f}")
                console.print(f"  ✓ Saved Multi-LLM logs to {output_dir}/multi_llm/")
                
                # Add ronten analysis to overall summary
                overall_summary.ronten_summaries = ronten_summaries
                overall_summary.novel_insights = novel_insights
            else:
                # Use single LLM for overall summary
                task = progress.add_task("[cyan]Generating overall summary...", total=None)
                overall_summary = await overall_summarizer.generate_summary(
                    survey_title=extraction_result.survey_title,
                    total_responses=extraction_result.response_count,
                    date_range=extraction_result.date_range,
                    stance_distribution=stance_distribution,
                    cluster_summaries=cluster_summaries,
                    minority_opinions=minorities,
                    ronten_context=ronten_context,
                )
                progress.update(task, completed=True)
                
                # Add ronten analysis to overall summary
                overall_summary.ronten_summaries = ronten_summaries
                overall_summary.novel_insights = novel_insights
            
            # Persona analysis
            persona_result = None
            if persona:
                task = progress.add_task("[cyan]Running persona analysis...", total=None)
                persona_assembly = PersonaAssembly(settings, llm_client)
                
                # Prepare content for persona analysis
                content = f"""
## アンケート分析結果

### 基本情報
- タイトル: {extraction_result.survey_title}
- 総回答数: {extraction_result.response_count}

### 主要な発見
{chr(10).join(f"- {f}" for f in overall_summary.key_findings[:5])}

### 合意点
{chr(10).join(f"- {p}" for p in overall_summary.consensus_points[:3])}

### 対立点
{chr(10).join(f"- {p}" for p in overall_summary.disagreement_points[:3])}

### マイノリティ意見
{chr(10).join(f"- {m.content[:100]}..." for m in minorities[:3])}
"""
                persona_result = await persona_assembly.assemble_analysis(content)
                progress.update(task, completed=True)
                console.print(f"  ✓ Persona analysis completed ({len(persona_result.individual_analyses)} perspectives)")
        
        # Phase 4: Generate outputs
        if overall_summary:
            task = progress.add_task("[cyan]Generating report...", total=None)
            report_generator = ReportGenerator(settings)
            
            report_data = ReportData(
                overall_summary=overall_summary,
                persona_analysis=persona_result.to_dict() if persona_result else None,
                multi_llm_consensus=multi_llm_result.to_dict() if multi_llm_result else None,
                filter_stats=filter_stats.to_dict() if filter_stats else None,
            )
            
            outputs = report_generator.save_report(
                report_data,
                output_dir,
                formats=['md', 'html'],
            )
            progress.update(task, completed=True)
            
            for fmt, path in outputs.items():
                console.print(f"  ✓ Saved {fmt}: {path}")
        
        # Build cluster details for visualization (use all clusters for full picture)
        import json
        
        cluster_details = []
        for c in clusters_all:
            cluster_details.append({
                "cluster_id": int(c.cluster_id),  # Convert numpy int64 to Python int
                "label": c.label,
                "size": int(c.size),
                "keywords": c.keywords,
                "sample_responses": [r.content[:200] for r in c.responses[:3]],
                "included_in_report": c.size >= settings.min_cluster_size_for_report,
            })
        
        # Sort by size descending
        cluster_details.sort(key=lambda x: x['size'], reverse=True)
        
        # Charts
        if not skip_charts:
            task = progress.add_task("[cyan]Generating charts...", total=None)
            chart_generator = ChartGenerator(settings)
            
            analysis_results = {
                'stance_distribution': stance_distribution,
                'cluster_summaries': [cs.to_dict() for cs in cluster_summaries] if cluster_summaries else [],
                'cluster_details': cluster_details,
                'response_texts': [r.content for r in filtered_responses],
            }
            
            chart_outputs = chart_generator.generate_all_charts(
                analysis_results,
                output_dir,
            )
            progress.update(task, completed=True)
            
            for name, path in chart_outputs.items():
                console.print(f"  ✓ Chart: {path}")
        
        # RAG Index
        if not skip_index and overall_summary:
            task = progress.add_task("[cyan]Building RAG index...", total=None)
            index_builder = IndexBuilder(settings)
            
            report_content = report_generator.generate_markdown(report_data) if overall_summary else ""
            
            index_path = index_builder.build_index(
                survey_slug=survey_slug,
                responses=extraction_result.responses,
                report_content=report_content,
                cluster_summaries=[cs.to_dict() for cs in cluster_summaries],
                output_dir=output_dir,
            )
            progress.update(task, completed=True)
            console.print(f"  ✓ Index: {index_path}")
        
        analysis_data = {
            "survey_slug": survey_slug,
            "survey_title": extraction_result.survey_title,
            "generated_at": datetime.now().isoformat(),
            "response_count": extraction_result.response_count,
            "stance_distribution": stance_distribution,
            "cluster_count": len(clusters_all),
            "cluster_count_in_report": len(clusters),
            "min_cluster_size_for_report": settings.min_cluster_size_for_report,
            "cluster_details": cluster_details,
            "minority_count": len(minorities),
            "minority_opinions": [
                {
                    "content": m.content[:300],
                    "outlier_score": m.outlier_score,
                    "uniqueness_reason": m.uniqueness_reason,
                    "unique_keywords": m.unique_keywords[:5] if m.unique_keywords else [],
                }
                for m in minorities[:20]  # Top 20 minorities
            ],
            "settings": {
                "provider": settings.llm_provider.value,
                "multi_llm": multi_llm,
                "persona": persona,
            }
        }
        
        data_path = output_dir / "analysis_data.json"
        with open(data_path, 'w', encoding='utf-8') as f:
            json.dump(analysis_data, f, ensure_ascii=False, indent=2)
        
        console.print(f"\n[bold green]✓ Analysis complete![/bold green]")
        console.print(f"Output directory: {output_dir}")


@app.command()
def batch(
    config_file: Path = typer.Argument(..., help="YAML config file for batch processing"),
    provider: Optional[str] = typer.Option(
        None, "--provider", "-p",
        help="Override LLM provider"
    ),
):
    """Run batch analysis from config file."""
    import yaml
    
    if not config_file.exists():
        console.print(f"[red]Config file not found: {config_file}[/red]")
        raise typer.Exit(1)
    
    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    jobs = config.get('jobs', [])
    
    console.print(Panel(
        f"[bold blue]Batch Processing[/bold blue]\n"
        f"Jobs: {len(jobs)}",
        title="Survey Analysis Pipeline",
    ))
    
    for i, job in enumerate(jobs, 1):
        console.print(f"\n[bold]Job {i}/{len(jobs)}:[/bold] {job.get('survey_slug', 'Unknown')}")
        
        try:
            asyncio.run(_run_pipeline(
                survey_slug=job['survey_slug'],
                output_dir=Path(job.get('output_dir', f"outputs/{job['survey_slug']}")),
                settings=get_settings_with_provider(provider or job.get('provider')),
                multi_llm=job.get('multi_llm', False),
                persona=job.get('persona', False),
                skip_summarization=job.get('skip_summarization', False),
                skip_charts=job.get('skip_charts', False),
                skip_index=job.get('skip_index', False),
            ))
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            continue
    
    console.print(f"\n[bold green]✓ Batch processing complete![/bold green]")


@app.command()
def query(
    survey_slug: str = typer.Argument(..., help="Survey slug to query"),
    question: str = typer.Argument(..., help="Question to ask"),
    output_dir: Optional[Path] = typer.Option(
        None, "--output", "-o",
        help="Output directory containing index"
    ),
):
    """Query the RAG index for a survey."""
    settings = get_settings()
    
    if output_dir is None:
        output_dir = Path(settings.output_dir) / survey_slug
    
    index_dir = output_dir / "vector_index"
    
    if not index_dir.exists():
        console.print(f"[red]Index not found: {index_dir}[/red]")
        console.print("Run 'analyze' first to build the index.")
        raise typer.Exit(1)
    
    index_builder = IndexBuilder(settings)
    results = index_builder.query_index(index_dir, question, n_results=5)
    
    console.print(f"\n[bold]Query:[/bold] {question}\n")
    
    for i, result in enumerate(results, 1):
        console.print(Panel(
            f"[dim]{result['content'][:300]}...[/dim]" if len(result['content']) > 300 else result['content'],
            title=f"Result {i} ({result['metadata'].get('type', 'unknown')})",
            border_style="blue",
        ))


@app.command("build-index")
def build_index(
    survey_slug: str = typer.Argument(..., help="Survey slug to build index for"),
    output_dir: Optional[Path] = typer.Option(
        None, "--output", "-o",
        help="Output directory for index"
    ),
    include_raw_data: bool = typer.Option(
        True, "--include-raw/--no-raw",
        help="Include raw survey responses in index"
    ),
):
    """Build RAG index for a survey (can be run independently).
    
    This command builds a ChromaDB vector index from:
    - report.md (if exists)
    - analysis_data.json (if exists)
    - Raw survey responses from CSV (if --include-raw)
    """
    settings = get_settings()
    
    if output_dir is None:
        output_dir = Path(settings.output_dir) / survey_slug
    output_dir.mkdir(parents=True, exist_ok=True)
    
    console.print(Panel(
        f"[bold blue]Building RAG Index: {survey_slug}[/bold blue]\n"
        f"Include raw data: {'Yes' if include_raw_data else 'No'}",
        title="RAG Index Builder",
    ))
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        
        # Load existing analysis data if available
        analysis_data = None
        analysis_data_path = output_dir / "analysis_data.json"
        if analysis_data_path.exists():
            task = progress.add_task("[cyan]Loading analysis data...", total=None)
            import json
            with open(analysis_data_path, 'r', encoding='utf-8') as f:
                analysis_data = json.load(f)
            progress.update(task, completed=True)
            console.print(f"  ✓ Loaded analysis data")
        
        # Load report if available
        report_content = ""
        report_path = output_dir / "report.md"
        if report_path.exists():
            task = progress.add_task("[cyan]Loading report...", total=None)
            with open(report_path, 'r', encoding='utf-8') as f:
                report_content = f.read()
            progress.update(task, completed=True)
            console.print(f"  ✓ Loaded report ({len(report_content)} chars)")
        
        # Load raw responses if requested
        responses = []
        if include_raw_data:
            task = progress.add_task("[cyan]Extracting raw responses...", total=None)
            extractor = ResponseExtractor(settings)
            try:
                extraction_result = extractor.extract_responses(survey_slug)
                responses = extraction_result.responses
                progress.update(task, completed=True)
                console.print(f"  ✓ Extracted {len(responses)} raw responses")
            except Exception as e:
                progress.update(task, completed=True)
                console.print(f"  [yellow]⚠ Could not load raw data: {e}[/yellow]")
        
        # Build index
        task = progress.add_task("[cyan]Building vector index...", total=None)
        index_builder = IndexBuilder(settings)
        
        # Prepare cluster summaries from analysis data
        cluster_summaries = []
        if analysis_data and 'cluster_details' in analysis_data:
            cluster_summaries = [
                {
                    'cluster_id': c.get('cluster_id', 0),
                    'cluster_label': c.get('label', ''),
                    'group_assertion': f"クラスタ {c.get('label', '')} ({c.get('size', 0)}件)",
                    'main_points': c.get('keywords', []),
                    'response_count': c.get('size', 0),
                }
                for c in analysis_data['cluster_details']
            ]
        
        index_path = index_builder.build_index(
            survey_slug=survey_slug,
            responses=responses,
            report_content=report_content,
            cluster_summaries=cluster_summaries,
            output_dir=output_dir,
        )
        progress.update(task, completed=True)
        
        # Get index stats
        metadata_path = index_path / "metadata.json"
        if metadata_path.exists():
            import json
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            console.print(f"\n[bold green]✓ Index built successfully![/bold green]")
            console.print(f"  Collection: {metadata.get('collection_name', 'unknown')}")
            console.print(f"  Responses indexed: {metadata.get('response_count', 0)}")
            console.print(f"  Clusters indexed: {metadata.get('cluster_count', 0)}")
            console.print(f"  Path: {index_path}")


@app.command("serve-index")
def serve_index(
    survey_slug: str = typer.Argument(..., help="Survey slug to serve index for"),
    output_dir: Optional[Path] = typer.Option(
        None, "--output", "-o",
        help="Output directory containing index"
    ),
    port: int = typer.Option(
        8000, "--port", "-p",
        help="Port to serve ChromaDB on"
    ),
    host: str = typer.Option(
        "localhost", "--host", "-h",
        help="Host to bind to"
    ),
):
    """Start ChromaDB server for RAG queries.
    
    This starts a ChromaDB HTTP server that can be queried from Next.js.
    The server will serve the vector index for the specified survey.
    
    Example:
        pixi run python main.py serve-index bill-of-lading --port 8000
    
    Then connect from Next.js with:
        const client = new ChromaClient({ path: "http://localhost:8000" });
    """
    settings = get_settings()
    
    if output_dir is None:
        output_dir = Path(settings.output_dir) / survey_slug
    
    index_dir = output_dir / "vector_index"
    
    if not index_dir.exists():
        console.print(f"[red]Index not found: {index_dir}[/red]")
        console.print("Run 'build-index' first to create the index.")
        raise typer.Exit(1)
    
    # Check for metadata
    metadata_path = index_dir / "metadata.json"
    if not metadata_path.exists():
        console.print(f"[red]Index metadata not found: {metadata_path}[/red]")
        raise typer.Exit(1)
    
    import json
    with open(metadata_path, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    
    console.print(Panel(
        f"[bold blue]Starting ChromaDB Server[/bold blue]\n"
        f"Survey: {survey_slug}\n"
        f"Collection: {metadata.get('collection_name', 'unknown')}\n"
        f"Documents: {metadata.get('response_count', 0)} responses, {metadata.get('cluster_count', 0)} clusters\n"
        f"URL: http://{host}:{port}",
        title="RAG Server",
    ))
    
    console.print(f"\n[yellow]Press Ctrl+C to stop the server[/yellow]\n")
    
    # Start ChromaDB server
    import subprocess
    import shutil
    
    try:
        # Find chroma executable
        chroma_path = shutil.which("chroma")
        if not chroma_path:
            # Try in pixi environment
            import sys
            env_bin = Path(sys.executable).parent
            chroma_path = env_bin / "chroma"
            if not chroma_path.exists():
                console.print("[red]chroma CLI not found[/red]")
                console.print("Install with: pip install chromadb")
                raise typer.Exit(1)
        
        # Use chroma CLI to start server
        cmd = [
            str(chroma_path),
            "run",
            "--path", str(index_dir),
            "--host", host,
            "--port", str(port),
        ]
        
        console.print(f"[dim]Running: {' '.join(cmd)}[/dim]\n")
        
        process = subprocess.run(cmd)
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped[/yellow]")
    except Exception as e:
        console.print(f"[red]Error starting server: {e}[/red]")
        console.print("\n[yellow]Alternative: You can also run ChromaDB server directly:[/yellow]")
        console.print(f"  chroma run --path {index_dir} --host {host} --port {port}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()

