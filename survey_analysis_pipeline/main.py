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
from pipeline.analyzers.stance_detector import StanceDetector
from pipeline.analyzers.topic_clusterer import TopicClusterer
from pipeline.analyzers.minority_detector import MinorityDetector
from pipeline.summarizers.cluster_summarizer import ClusterSummarizer
from pipeline.summarizers.overall_summarizer import OverallSummarizer
from pipeline.generators.report_generator import ReportGenerator, ReportData
from pipeline.generators.chart_generator import ChartGenerator
from pipeline.generators.index_builder import IndexBuilder
from orchestration.multi_llm import MultiLLMOrchestrator
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
        
        # Phase 2: Analyze
        task = progress.add_task("[cyan]Detecting stances...", total=None)
        stance_detector = StanceDetector()
        stance_results = stance_detector.analyze_responses(extraction_result.responses)
        stance_distribution = stance_detector.get_stance_distribution(stance_results)
        progress.update(task, completed=True)
        
        task = progress.add_task("[cyan]Clustering responses...", total=None)
        clusterer = TopicClusterer(settings)
        clusters = clusterer.cluster_responses(extraction_result.responses)
        progress.update(task, completed=True)
        
        console.print(f"  ✓ Found {len(clusters)} clusters")
        
        task = progress.add_task("[cyan]Detecting minority opinions...", total=None)
        minority_detector = MinorityDetector(settings)
        minorities = minority_detector.detect_minorities(extraction_result.responses)
        progress.update(task, completed=True)
        
        console.print(f"  ✓ Found {len(minorities)} minority opinions")
        
        # Phase 3: Summarize with LLM
        cluster_summaries = []
        overall_summary = None
        
        if not skip_summarization:
            llm_client = LLMClient(settings)
            
            task = progress.add_task("[cyan]Summarizing clusters...", total=None)
            cluster_summarizer = ClusterSummarizer(settings, llm_client)
            cluster_summaries = await cluster_summarizer.summarize_all_clusters(clusters)
            progress.update(task, completed=True)
            
            task = progress.add_task("[cyan]Generating overall summary...", total=None)
            overall_summarizer = OverallSummarizer(settings, llm_client)
            overall_summary = await overall_summarizer.generate_summary(
                survey_title=extraction_result.survey_title,
                total_responses=extraction_result.response_count,
                date_range=extraction_result.date_range,
                stance_distribution=stance_distribution,
                cluster_summaries=cluster_summaries,
                minority_opinions=minorities,
            )
            progress.update(task, completed=True)
            
            # Multi-LLM orchestration
            multi_llm_result = None
            if multi_llm:
                task = progress.add_task("[cyan]Running multi-LLM consensus...", total=None)
                orchestrator = MultiLLMOrchestrator(settings)
                # Run consensus on executive summary
                consensus_prompt = f"""
以下のアンケート分析結果について、総合的な評価と推奨事項を提供してください：

タイトル: {extraction_result.survey_title}
回答数: {extraction_result.response_count}

立場分布:
{chr(10).join(f"- {k}: {v['count']}件" for k, v in stance_distribution.items())}

主要クラスタ:
{chr(10).join(f"- {cs.cluster_label}: {cs.group_assertion}" for cs in cluster_summaries[:3])}
"""
                multi_llm_result = await orchestrator.reach_consensus(consensus_prompt)
                progress.update(task, completed=True)
                console.print(f"  ✓ Multi-LLM agreement score: {multi_llm_result.agreement_score:.2f}")
            
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
            )
            
            outputs = report_generator.save_report(
                report_data,
                output_dir,
                formats=['md', 'html'],
            )
            progress.update(task, completed=True)
            
            for fmt, path in outputs.items():
                console.print(f"  ✓ Saved {fmt}: {path}")
        
        # Charts
        if not skip_charts:
            task = progress.add_task("[cyan]Generating charts...", total=None)
            chart_generator = ChartGenerator(settings)
            
            analysis_results = {
                'stance_distribution': stance_distribution,
                'cluster_summaries': [cs.to_dict() for cs in cluster_summaries] if cluster_summaries else [],
                'response_texts': [r.content for r in extraction_result.responses],
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
        
        # Save analysis data
        import json
        analysis_data = {
            "survey_slug": survey_slug,
            "survey_title": extraction_result.survey_title,
            "generated_at": datetime.now().isoformat(),
            "response_count": extraction_result.response_count,
            "stance_distribution": stance_distribution,
            "cluster_count": len(clusters),
            "minority_count": len(minorities),
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


if __name__ == "__main__":
    app()

