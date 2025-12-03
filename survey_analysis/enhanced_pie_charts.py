#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Pie Chart Module
感情分析に基づく色分けされたパイチャート生成
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
from typing import Dict, List, Tuple, Optional


class EnhancedPieChartGenerator:
    """
    Generate enhanced pie charts with sentiment-based coloring
    """
    
    def __init__(self):
        # 日本語フォント設定
        plt.rcParams['font.sans-serif'] = ['Hiragino Sans', 'Yu Gothic', 'Meiryo', 'MS Gothic', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        
        # Sentiment-based color schemes
        self.sentiment_colors = {
            'positive': '#2ecc71',  # Green
            'negative': '#e74c3c',  # Red
            'neutral': '#95a5a6',   # Gray
            'mixed': '#3498db',     # Blue
        }
        
        # Default color palette (for non-sentiment charts)
        self.default_colors = [
            '#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6',
            '#1abc9c', '#34495e', '#e67e22', '#95a5a6', '#c0392b',
            '#16a085', '#27ae60', '#2980b9', '#8e44ad', '#f1c40f',
        ]
    
    def _get_sentiment_color(self, sentiment_dist: Dict[str, int]) -> str:
        """
        Get color based on sentiment distribution
        
        Args:
            sentiment_dist: Dictionary with 'positive', 'negative', 'neutral' counts
            
        Returns:
            Color hex code
        """
        total = sum(sentiment_dist.values())
        if total == 0:
            return self.sentiment_colors['neutral']
        
        positive_pct = sentiment_dist.get('positive', 0) / total
        negative_pct = sentiment_dist.get('negative', 0) / total
        
        # Determine dominant sentiment
        if positive_pct > 0.6:
            return self.sentiment_colors['positive']
        elif negative_pct > 0.6:
            return self.sentiment_colors['negative']
        elif positive_pct > 0.4 or negative_pct > 0.4:
            return self.sentiment_colors['mixed']
        else:
            return self.sentiment_colors['neutral']
    
    def _get_gradient_colors(self, n: int, base_color: str = '#3498db') -> List[str]:
        """
        Generate gradient colors
        
        Args:
            n: Number of colors to generate
            base_color: Base color for gradient
            
        Returns:
            List of color hex codes
        """
        if n <= len(self.default_colors):
            return self.default_colors[:n]
        
        # Generate gradient
        colors = []
        for i in range(n):
            intensity = 0.5 + (0.5 * i / n)
            # Simple color variation
            colors.append(self.default_colors[i % len(self.default_colors)])
        
        return colors
    
    def create_basic_pie_chart(
        self,
        categories: Dict[str, List],
        title: str,
        output_path: str,
        figsize: Tuple[int, int] = (12, 8)
    ) -> str:
        """
        Create basic pie chart
        
        Args:
            categories: Dictionary mapping category names to response lists
            title: Chart title
            output_path: Output file path
            figsize: Figure size
            
        Returns:
            Path to saved chart
        """
        if not categories:
            print(f"No data to create pie chart for: {title}")
            return None
        
        # Prepare data
        labels = []
        sizes = []
        
        for category, responses in sorted(categories.items(), key=lambda x: len(x[1]), reverse=True):
            labels.append(f"{category}\n({len(responses)}件)")
            sizes.append(len(responses))
        
        # Create figure
        fig, ax = plt.subplots(figsize=figsize)
        
        # Get colors
        colors = self._get_gradient_colors(len(labels))
        
        # Create pie chart
        wedges, texts, autotexts = ax.pie(
            sizes,
            labels=labels,
            colors=colors,
            autopct='%1.1f%%',
            startangle=90,
            textprops={'fontsize': 10}
        )
        
        # Enhance text
        for text in texts:
            text.set_fontsize(11)
        
        for autotext in autotexts:
            autotext.set_fontsize(9)
            autotext.set_color('white')
            autotext.set_weight('bold')
        
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"Saved pie chart: {output_path}")
        return output_path
    
    def create_sentiment_pie_chart(
        self,
        categories: Dict[str, Dict],
        title: str,
        output_path: str,
        figsize: Tuple[int, int] = (14, 8)
    ) -> str:
        """
        Create pie chart with sentiment-based coloring
        
        Args:
            categories: Dictionary mapping category names to category data
                       (must include 'responses' and 'sentiment' keys)
            title: Chart title
            output_path: Output file path
            figsize: Figure size
            
        Returns:
            Path to saved chart
        """
        if not categories:
            print(f"No data to create pie chart for: {title}")
            return None
        
        # Prepare data
        labels = []
        sizes = []
        colors = []
        
        for category, category_data in sorted(
            categories.items(),
            key=lambda x: len(x[1].get('responses', [])),
            reverse=True
        ):
            responses = category_data.get('responses', [])
            sentiment = category_data.get('sentiment', {})
            
            labels.append(f"{category}\n({len(responses)}件)")
            sizes.append(len(responses))
            
            # Get color based on sentiment
            color = self._get_sentiment_color(sentiment)
            colors.append(color)
        
        # Create figure with two subplots
        fig = plt.figure(figsize=figsize)
        
        # Main pie chart
        ax1 = plt.subplot(1, 2, 1)
        wedges, texts, autotexts = ax1.pie(
            sizes,
            labels=labels,
            colors=colors,
            autopct='%1.1f%%',
            startangle=90,
            textprops={'fontsize': 10}
        )
        
        # Enhance text
        for text in texts:
            text.set_fontsize(11)
        
        for autotext in autotexts:
            autotext.set_fontsize(9)
            autotext.set_color('white')
            autotext.set_weight('bold')
        
        ax1.set_title(title, fontsize=14, fontweight='bold', pad=20)
        
        # Legend for sentiment colors
        ax2 = plt.subplot(1, 2, 2)
        ax2.axis('off')
        
        # Create sentiment legend
        sentiment_patches = [
            mpatches.Patch(color=self.sentiment_colors['positive'], label='肯定的 (60%以上)'),
            mpatches.Patch(color=self.sentiment_colors['mixed'], label='混合 (40-60%)'),
            mpatches.Patch(color=self.sentiment_colors['neutral'], label='中立'),
            mpatches.Patch(color=self.sentiment_colors['negative'], label='否定的 (60%以上)'),
        ]
        
        ax2.legend(
            handles=sentiment_patches,
            loc='center',
            fontsize=12,
            title='感情分析による色分け',
            title_fontsize=13,
            frameon=True,
            fancybox=True,
            shadow=True
        )
        
        # Add category details text
        details_text = "カテゴリ別詳細:\n\n"
        for category, category_data in list(categories.items())[:5]:  # Top 5
            responses = category_data.get('responses', [])
            sentiment = category_data.get('sentiment', {})
            total = len(responses)
            
            pos = sentiment.get('positive', 0)
            neg = sentiment.get('negative', 0)
            neu = sentiment.get('neutral', 0)
            
            details_text += f"{category}: {total}件\n"
            if total > 0:
                details_text += f"  肯定:{pos} 否定:{neg} 中立:{neu}\n"
        
        ax2.text(
            0.1, 0.3,
            details_text,
            fontsize=10,
            verticalalignment='top',
            family='monospace',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3)
        )
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"Saved sentiment pie chart: {output_path}")
        return output_path
    
    def create_hierarchical_chart(
        self,
        categories: Dict[str, Dict],
        title: str,
        output_path: str,
        figsize: Tuple[int, int] = (14, 10)
    ) -> str:
        """
        Create hierarchical/nested pie chart
        
        Args:
            categories: Dictionary with category data including subcategories
            title: Chart title
            output_path: Output file path
            figsize: Figure size
            
        Returns:
            Path to saved chart
        """
        # This is a placeholder for future hierarchical chart implementation
        # For now, create a regular sentiment chart
        return self.create_sentiment_pie_chart(categories, title, output_path, figsize)
    
    def create_multi_chart_comparison(
        self,
        survey_data: Dict[str, Dict],
        output_path: str,
        figsize: Tuple[int, int] = (16, 12)
    ) -> str:
        """
        Create multiple pie charts for comparison
        
        Args:
            survey_data: Dictionary mapping survey names to their category data
            output_path: Output file path
            figsize: Figure size
            
        Returns:
            Path to saved chart
        """
        n_surveys = len(survey_data)
        if n_surveys == 0:
            return None
        
        # Calculate grid layout
        cols = min(3, n_surveys)
        rows = (n_surveys + cols - 1) // cols
        
        fig, axes = plt.subplots(rows, cols, figsize=figsize)
        if n_surveys == 1:
            axes = [axes]
        else:
            axes = axes.flatten()
        
        for idx, (survey_name, categories) in enumerate(survey_data.items()):
            ax = axes[idx]
            
            # Prepare data
            labels = []
            sizes = []
            colors = []
            
            for category, category_data in sorted(
                categories.items(),
                key=lambda x: len(x[1].get('responses', [])),
                reverse=True
            ):
                responses = category_data.get('responses', [])
                sentiment = category_data.get('sentiment', {})
                
                labels.append(f"{category}\n({len(responses)})")
                sizes.append(len(responses))
                colors.append(self._get_sentiment_color(sentiment))
            
            # Create pie chart
            wedges, texts, autotexts = ax.pie(
                sizes,
                labels=labels,
                colors=colors,
                autopct='%1.1f%%',
                startangle=90,
                textprops={'fontsize': 8}
            )
            
            for autotext in autotexts:
                autotext.set_fontsize(7)
                autotext.set_color('white')
                autotext.set_weight('bold')
            
            ax.set_title(survey_name, fontsize=11, fontweight='bold')
        
        # Hide unused subplots
        for idx in range(n_surveys, len(axes)):
            axes[idx].axis('off')
        
        plt.suptitle('アンケート比較', fontsize=16, fontweight='bold', y=0.98)
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"Saved comparison chart: {output_path}")
        return output_path


def test_enhanced_pie_charts():
    """Test function for enhanced pie charts"""
    import os
    
    # Sample data
    sample_categories = {
        '政治の透明性': {
            'responses': [{'content': f'回答{i}'} for i in range(30)],
            'sentiment': {'positive': 20, 'negative': 5, 'neutral': 5}
        },
        'DX推進': {
            'responses': [{'content': f'回答{i}'} for i in range(25)],
            'sentiment': {'positive': 18, 'negative': 3, 'neutral': 4}
        },
        '選挙制度改革': {
            'responses': [{'content': f'回答{i}'} for i in range(15)],
            'sentiment': {'positive': 5, 'negative': 8, 'neutral': 2}
        },
        'その他': {
            'responses': [{'content': f'回答{i}'} for i in range(10)],
            'sentiment': {'positive': 3, 'negative': 3, 'neutral': 4}
        },
    }
    
    generator = EnhancedPieChartGenerator()
    
    output_dir = '/Users/masa/forback/github/mirai_DB_backup/survey_analysis'
    os.makedirs(output_dir, exist_ok=True)
    
    # Test sentiment pie chart
    output_path = os.path.join(output_dir, 'test_sentiment_pie_chart.png')
    generator.create_sentiment_pie_chart(
        sample_categories,
        'テストアンケート - 感情分析付き',
        output_path
    )
    
    print(f"Test chart saved to: {output_path}")


if __name__ == '__main__':
    test_enhanced_pie_charts()









