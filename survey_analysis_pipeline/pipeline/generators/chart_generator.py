"""Generate charts and visualizations."""

from pathlib import Path
from typing import Dict, Any, List, Optional
import json

import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend

from config.settings import Settings, get_settings


# Set Japanese font for matplotlib
plt.rcParams['font.family'] = ['Hiragino Sans', 'Yu Gothic', 'Meirio', 'sans-serif']


class ChartGenerator:
    """Generate charts and visualizations."""
    
    def __init__(self, settings: Optional[Settings] = None):
        """Initialize chart generator.
        
        Args:
            settings: Application settings
        """
        self.settings = settings or get_settings()
    
    def generate_stance_pie_chart(
        self,
        stance_distribution: Dict[str, Dict[str, Any]],
        output_path: Path,
    ) -> Path:
        """Generate pie chart for stance distribution.
        
        Args:
            stance_distribution: Stance data with counts and percentages
            output_path: Path to save the chart
            
        Returns:
            Path to saved chart
        """
        # Prepare data
        labels = []
        sizes = []
        colors = {
            "賛成": "#4CAF50",
            "反対": "#F44336",
            "中立/不明": "#9E9E9E",
            "条件付き": "#FF9800",
        }
        chart_colors = []
        
        for stance, data in stance_distribution.items():
            if data['count'] > 0:
                labels.append(f"{stance}\n({data['count']}件)")
                sizes.append(data['count'])
                chart_colors.append(colors.get(stance, "#2196F3"))
        
        if not sizes:
            return None
        
        # Create pie chart
        fig, ax = plt.subplots(figsize=(10, 8))
        wedges, texts, autotexts = ax.pie(
            sizes,
            labels=labels,
            colors=chart_colors,
            autopct='%1.1f%%',
            startangle=90,
            pctdistance=0.75,
        )
        
        # Style
        for autotext in autotexts:
            autotext.set_fontsize(12)
            autotext.set_fontweight('bold')
        
        for text in texts:
            text.set_fontsize(11)
        
        ax.set_title('回答者の立場分布', fontsize=16, fontweight='bold', pad=20)
        
        # Save
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        
        return output_path
    
    def generate_cluster_bar_chart(
        self,
        cluster_summaries: List[Dict[str, Any]],
        output_path: Path,
    ) -> Path:
        """Generate bar chart for cluster sizes.
        
        Args:
            cluster_summaries: List of cluster summary dicts
            output_path: Path to save the chart
            
        Returns:
            Path to saved chart
        """
        if not cluster_summaries:
            return None
        
        # Prepare data
        labels = [cs['cluster_label'] for cs in cluster_summaries]
        sizes = [cs['response_count'] for cs in cluster_summaries]
        
        # Create bar chart
        fig, ax = plt.subplots(figsize=(12, 6))
        
        bars = ax.barh(labels, sizes, color='#2196F3')
        
        # Add value labels
        for bar, size in zip(bars, sizes):
            ax.text(
                bar.get_width() + 1,
                bar.get_y() + bar.get_height() / 2,
                f'{size}件',
                va='center',
                fontsize=11,
            )
        
        ax.set_xlabel('回答数', fontsize=12)
        ax.set_title('クラスタ別回答数', fontsize=16, fontweight='bold')
        ax.invert_yaxis()  # Largest at top
        
        # Save
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        
        return output_path
    
    def generate_wordcloud(
        self,
        texts: List[str],
        output_path: Path,
    ) -> Path:
        """Generate word cloud from texts.
        
        Args:
            texts: List of text strings
            output_path: Path to save the image
            
        Returns:
            Path to saved image
        """
        from wordcloud import WordCloud
        
        # Combine texts
        combined_text = ' '.join(texts)
        
        # Try to use Japanese font
        font_path = None
        font_paths = [
            '/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc',
            '/System/Library/Fonts/Hiragino Sans GB.ttc',
            '/usr/share/fonts/truetype/fonts-japanese-gothic.ttf',
        ]
        
        for fp in font_paths:
            if Path(fp).exists():
                font_path = fp
                break
        
        # Generate word cloud
        wordcloud = WordCloud(
            width=1200,
            height=600,
            background_color='white',
            font_path=font_path,
            max_words=100,
            collocations=False,
            regexp=r'[\w\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]+',
        ).generate(combined_text)
        
        # Save
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.imshow(wordcloud, interpolation='bilinear')
        ax.axis('off')
        ax.set_title('頻出キーワード', fontsize=16, fontweight='bold')
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        
        return output_path
    
    def generate_cluster_treemap(
        self,
        cluster_details: List[Dict[str, Any]],
        output_path: Path,
    ) -> Path:
        """Generate treemap for cluster distribution.
        
        Args:
            cluster_details: List of cluster info with size and keywords
            output_path: Path to save the chart
            
        Returns:
            Path to saved chart
        """
        import plotly.express as px
        import plotly.io as pio
        
        if not cluster_details:
            return None
        
        # Prepare data for treemap
        labels = []
        sizes = []
        parents = []
        hover_texts = []
        
        # Root node
        total_size = sum(c['size'] for c in cluster_details)
        
        for c in cluster_details:
            label = c.get('label', f"クラスタ {c['cluster_id']}")
            keywords = c.get('keywords', [])[:3]
            size = c['size']
            
            # Create label with keywords
            if keywords:
                display_label = f"{label}<br>({', '.join(keywords)})"
            else:
                display_label = label
            
            labels.append(display_label)
            sizes.append(size)
            parents.append("")  # Root level
            
            # Hover text with sample responses
            samples = c.get('sample_responses', [])
            hover = f"<b>{label}</b><br>回答数: {size}件<br>"
            if keywords:
                hover += f"キーワード: {', '.join(keywords)}<br>"
            if samples:
                hover += f"<br>サンプル: {samples[0][:100]}..."
            hover_texts.append(hover)
        
        # Create treemap
        fig = px.treemap(
            names=labels,
            parents=parents,
            values=sizes,
            title=f'クラスタ分布 (全{len(cluster_details)}クラスタ, {total_size}回答)',
        )
        
        fig.update_traces(
            hovertemplate='%{customdata}<extra></extra>',
            customdata=hover_texts,
            textinfo='label+value+percent root',
            textfont_size=12,
        )
        
        fig.update_layout(
            font=dict(family='Hiragino Sans, Yu Gothic, sans-serif'),
            margin=dict(t=50, l=25, r=25, b=25),
        )
        
        # Save as HTML (interactive)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        html_path = output_path.with_suffix('.html')
        pio.write_html(fig, html_path)
        
        # Also save as PNG (static)
        png_path = output_path.with_suffix('.png')
        try:
            fig.write_image(png_path, width=1200, height=800)
        except Exception:
            # Kaleido not installed, skip PNG
            pass
        
        return html_path
    
    def generate_top_clusters_bar_chart(
        self,
        cluster_details: List[Dict[str, Any]],
        output_path: Path,
        top_n: int = 15,
    ) -> Path:
        """Generate horizontal bar chart for top N clusters.
        
        Args:
            cluster_details: List of cluster info with size and keywords
            output_path: Path to save the chart
            top_n: Number of top clusters to show
            
        Returns:
            Path to saved chart
        """
        if not cluster_details:
            return None
        
        # Sort by size and take top N
        sorted_clusters = sorted(cluster_details, key=lambda x: x['size'], reverse=True)[:top_n]
        sorted_clusters.reverse()  # Reverse for bottom-to-top display
        
        # Prepare data
        labels = []
        sizes = []
        colors = []
        
        for c in sorted_clusters:
            keywords = c.get('keywords', [])[:2]
            label = c.get('label', f"クラスタ {c['cluster_id']}")
            
            if keywords:
                label = f"{label} ({', '.join(keywords)})"
            
            labels.append(label)
            sizes.append(c['size'])
            
            # Color based on cluster type
            if c.get('cluster_id') == -1:
                colors.append('#9E9E9E')  # Gray for noise
            else:
                colors.append('#2196F3')  # Blue for regular clusters
        
        # Create bar chart
        fig, ax = plt.subplots(figsize=(12, max(6, len(sorted_clusters) * 0.4)))
        
        bars = ax.barh(labels, sizes, color=colors)
        
        # Add value labels
        for bar, size in zip(bars, sizes):
            ax.text(
                bar.get_width() + max(sizes) * 0.01,
                bar.get_y() + bar.get_height() / 2,
                f'{size}件',
                va='center',
                fontsize=10,
            )
        
        ax.set_xlabel('回答数', fontsize=12)
        ax.set_title(f'上位{len(sorted_clusters)}クラスタの回答数分布', fontsize=14, fontweight='bold')
        ax.set_xlim(0, max(sizes) * 1.15)
        
        # Save
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        
        return output_path
    
    def generate_scatter_plot_data(
        self,
        embeddings_2d: List[List[float]],
        labels: List[int],
        texts: List[str],
        output_path: Path,
    ) -> Path:
        """Generate interactive scatter plot data for Plotly.
        
        Args:
            embeddings_2d: 2D embeddings for each response
            labels: Cluster labels
            texts: Response texts
            output_path: Path to save the JSON data
            
        Returns:
            Path to saved JSON file
        """
        # Prepare data for Plotly
        data = {
            "x": [e[0] for e in embeddings_2d],
            "y": [e[1] for e in embeddings_2d],
            "cluster": labels,
            "text": [t[:100] + "..." if len(t) > 100 else t for t in texts],
        }
        
        # Save as JSON for use in Next.js
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return output_path
    
    def generate_all_charts(
        self,
        analysis_results: Dict[str, Any],
        output_dir: Path,
    ) -> Dict[str, Path]:
        """Generate all charts for analysis results.
        
        Args:
            analysis_results: Complete analysis results
            output_dir: Directory for chart output
            
        Returns:
            Dictionary mapping chart name to output path
        """
        charts_dir = output_dir / "charts"
        charts_dir.mkdir(parents=True, exist_ok=True)
        
        outputs = {}
        
        # Stance pie chart
        if 'stance_distribution' in analysis_results:
            path = self.generate_stance_pie_chart(
                analysis_results['stance_distribution'],
                charts_dir / "stance_distribution.png",
            )
            if path:
                outputs['stance_distribution'] = path
        
        # Cluster bar chart (from LLM summaries)
        if 'cluster_summaries' in analysis_results and analysis_results['cluster_summaries']:
            path = self.generate_cluster_bar_chart(
                analysis_results['cluster_summaries'],
                charts_dir / "cluster_sizes.png",
            )
            if path:
                outputs['cluster_sizes'] = path
        
        # Cluster treemap (from cluster details)
        if 'cluster_details' in analysis_results and analysis_results['cluster_details']:
            path = self.generate_cluster_treemap(
                analysis_results['cluster_details'],
                charts_dir / "cluster_treemap",
            )
            if path:
                outputs['cluster_treemap'] = path
        
        # Top clusters bar chart
        if 'cluster_details' in analysis_results and analysis_results['cluster_details']:
            path = self.generate_top_clusters_bar_chart(
                analysis_results['cluster_details'],
                charts_dir / "top_clusters.png",
            )
            if path:
                outputs['top_clusters'] = path
        
        # Word cloud
        if 'response_texts' in analysis_results:
            path = self.generate_wordcloud(
                analysis_results['response_texts'],
                charts_dir / "wordcloud.png",
            )
            if path:
                outputs['wordcloud'] = path
        
        return outputs

