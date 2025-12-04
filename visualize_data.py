#!/usr/bin/env python3
"""
データビジュアル化スクリプト

matplotlib, seaborn, wordcloud等を使用してデータを可視化します
"""

import json
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['font.family'] = 'DejaVu Sans'  # Japanese font support
import seaborn as sns
from collections import Counter, defaultdict
from datetime import datetime
import re
import os

# Try to import optional libraries
try:
    from wordcloud import WordCloud
    HAS_WORDCLOUD = True
except ImportError:
    HAS_WORDCLOUD = False
    print("Warning: wordcloud not installed. Word cloud visualization will be skipped.")

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    print("Warning: pandas not installed. Some visualizations will be skipped.")


class DataVisualizer:
    def __init__(self, json_file_path: str, output_dir: str = "visualizations"):
        """Initialize visualizer"""
        print(f"Loading data from {json_file_path}...")
        with open(json_file_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        self.tables = self.data['tables']
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        print("Data loaded successfully!")
        
    def plot_topic_distribution(self):
        """Plot distribution of sessions and responses by topic"""
        configs = self.tables['interview_configs']
        sessions = self.tables['interview_sessions']
        messages = self.tables['messages']
        
        topic_data = []
        for config in configs:
            slug = config.get('slug', 'unknown')
            title = config.get('title', 'Unknown')
            
            topic_sessions = [s for s in sessions if s.get('slug') == slug]
            session_ids = {s['id'] for s in topic_sessions}
            topic_messages = [m for m in messages 
                            if m.get('session_id') in session_ids 
                            and m.get('role') == 'user']
            
            if len(topic_sessions) > 0:  # Only include topics with sessions
                topic_data.append({
                    'title': slug,  # Use slug instead of title for English labels
                    'sessions': len(topic_sessions),
                    'responses': len(topic_messages)
                })
        
        # Sort by sessions count
        topic_data.sort(key=lambda x: x['sessions'], reverse=True)
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
        
        # Sessions distribution
        titles = [d['title'] for d in topic_data]
        sessions_counts = [d['sessions'] for d in topic_data]
        
        ax1.barh(titles, sessions_counts, color='steelblue')
        ax1.set_xlabel('Number of Sessions', fontsize=12)
        ax1.set_title('Sessions Distribution by Topic', fontsize=14, fontweight='bold')
        ax1.grid(axis='x', alpha=0.3)
        
        # Responses distribution
        responses_counts = [d['responses'] for d in topic_data]
        ax2.barh(titles, responses_counts, color='coral')
        ax2.set_xlabel('Number of User Responses', fontsize=12)
        ax2.set_title('User Responses Distribution by Topic', fontsize=14, fontweight='bold')
        ax2.grid(axis='x', alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(f'{self.output_dir}/topic_distribution.png', dpi=300, bbox_inches='tight')
        print(f"Saved: {self.output_dir}/topic_distribution.png")
        plt.close()
    
    def plot_response_length_distribution(self):
        """Plot distribution of response text lengths"""
        messages = self.tables['messages']
        user_messages = [m for m in messages if m.get('role') == 'user']
        
        lengths = [len(m.get('content', '')) for m in user_messages]
        
        # Filter out extreme outliers for better visualization
        max_display_length = 2000
        filtered_lengths = [l for l in lengths if l <= max_display_length]
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
        
        # Histogram
        ax1.hist(filtered_lengths, bins=50, color='skyblue', edgecolor='black', alpha=0.7)
        ax1.set_xlabel('Response Length (characters)', fontsize=12)
        ax1.set_ylabel('Frequency', fontsize=12)
        ax1.set_title('Distribution of Response Lengths (up to 2000 chars)', fontsize=14, fontweight='bold')
        ax1.grid(axis='y', alpha=0.3)
        
        # Box plot
        ax2.boxplot([filtered_lengths], vert=True, patch_artist=True,
                    boxprops=dict(facecolor='lightblue', alpha=0.7))
        ax2.set_ylabel('Response Length (characters)', fontsize=12)
        ax2.set_title('Response Length Box Plot', fontsize=14, fontweight='bold')
        ax2.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(f'{self.output_dir}/response_length_distribution.png', dpi=300, bbox_inches='tight')
        print(f"Saved: {self.output_dir}/response_length_distribution.png")
        plt.close()
    
    def plot_completion_rate(self):
        """Plot completion rate by topic"""
        configs = self.tables['interview_configs']
        sessions = self.tables['interview_sessions']
        
        topic_completion = []
        for config in configs:
            slug = config.get('slug', 'unknown')
            title = config.get('title', 'Unknown')
            
            topic_sessions = [s for s in sessions if s.get('slug') == slug]
            if len(topic_sessions) == 0:
                continue
                
            completed = len([s for s in topic_sessions if s.get('status') == 'completed'])
            completion_rate = (completed / len(topic_sessions)) * 100
            
            topic_completion.append({
                'title': slug,  # Use slug instead of title for English labels
                'completion_rate': completion_rate,
                'total': len(topic_sessions),
                'completed': completed
            })
        
        topic_completion.sort(key=lambda x: x['completion_rate'], reverse=True)
        
        fig, ax = plt.subplots(figsize=(12, 8))
        
        titles = [d['title'] for d in topic_completion]
        rates = [d['completion_rate'] for d in topic_completion]
        
        bars = ax.barh(titles, rates, color='green', alpha=0.7)
        ax.set_xlabel('Completion Rate (%)', fontsize=12)
        ax.set_title('Session Completion Rate by Topic', fontsize=14, fontweight='bold')
        ax.set_xlim(0, 100)
        ax.grid(axis='x', alpha=0.3)
        
        # Add value labels
        for i, (bar, rate, data) in enumerate(zip(bars, rates, topic_completion)):
            ax.text(rate + 1, i, f'{rate:.1f}% ({data["completed"]}/{data["total"]})', 
                   va='center', fontsize=9)
        
        plt.tight_layout()
        plt.savefig(f'{self.output_dir}/completion_rate.png', dpi=300, bbox_inches='tight')
        print(f"Saved: {self.output_dir}/completion_rate.png")
        plt.close()
    
    def plot_time_series(self):
        """Plot time series of sessions and responses"""
        sessions = self.tables['interview_sessions']
        messages = self.tables['messages']
        
        # Parse timestamps
        session_dates = []
        for s in sessions:
            try:
                start_time = s.get('start_time')
                if start_time:
                    dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    session_dates.append(dt.date())
            except:
                pass
        
        message_dates = []
        for m in messages:
            if m.get('role') == 'user':
                try:
                    timestamp = m.get('timestamp')
                    if timestamp:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        message_dates.append(dt.date())
                except:
                    pass
        
        # Count by date
        session_counts = Counter(session_dates)
        message_counts = Counter(message_dates)
        
        # Get date range
        all_dates = sorted(set(list(session_counts.keys()) + list(message_counts.keys())))
        
        if not all_dates:
            print("No valid dates found for time series plot")
            return
        
        fig, ax = plt.subplots(figsize=(14, 6))
        
        dates = all_dates
        session_vals = [session_counts.get(d, 0) for d in dates]
        message_vals = [message_counts.get(d, 0) for d in dates]
        
        ax.plot(dates, session_vals, marker='o', label='Sessions', linewidth=2, markersize=4)
        ax.plot(dates, message_vals, marker='s', label='User Responses', linewidth=2, markersize=4)
        
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('Count', fontsize=12)
        ax.set_title('Time Series: Sessions and Responses Over Time', fontsize=14, fontweight='bold')
        ax.legend(fontsize=11)
        ax.grid(alpha=0.3)
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        plt.savefig(f'{self.output_dir}/time_series.png', dpi=300, bbox_inches='tight')
        print(f"Saved: {self.output_dir}/time_series.png")
        plt.close()
    
    def create_wordcloud(self, topic_slug: str = None, max_words: int = 100):
        """Create word cloud from user responses"""
        if not HAS_WORDCLOUD:
            print("Skipping word cloud: wordcloud library not installed")
            return
        
        messages = self.tables['messages']
        sessions = self.tables['interview_sessions']
        
        # Filter by topic if specified
        if topic_slug:
            topic_sessions = [s for s in sessions if s.get('slug') == topic_slug]
            session_ids = {s['id'] for s in topic_sessions}
            user_messages = [m.get('content', '') for m in messages 
                           if m.get('session_id') in session_ids and m.get('role') == 'user']
            title_suffix = f" - {topic_slug}"
        else:
            user_messages = [m.get('content', '') for m in messages if m.get('role') == 'user']
            title_suffix = " - All Topics"
        
        # Combine all text
        text = ' '.join(user_messages)
        
        if not text:
            print(f"No text found for word cloud{topic_slug if topic_slug else ''}")
            return
        
        # Create word cloud
        wordcloud = WordCloud(
            width=1600, 
            height=800,
            background_color='white',
            max_words=max_words,
            colormap='viridis',
            font_path=None  # You may need to specify a Japanese font path
        ).generate(text)
        
        plt.figure(figsize=(16, 8))
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis('off')
        plt.title(f'Word Cloud{title_suffix}', fontsize=16, fontweight='bold', pad=20)
        
        filename = f'wordcloud_{topic_slug if topic_slug else "all"}.png'
        plt.savefig(f'{self.output_dir}/{filename}', dpi=300, bbox_inches='tight')
        print(f"Saved: {self.output_dir}/{filename}")
        plt.close()
    
    def generate_all_visualizations(self):
        """Generate all visualizations"""
        print("\nGenerating visualizations...")
        print("-" * 80)
        
        self.plot_topic_distribution()
        self.plot_response_length_distribution()
        self.plot_completion_rate()
        self.plot_time_series()
        
        # Create word clouds for top topics
        top_topics = ['teisuu', 'ai-plan-test', 'plan2026-public']
        for topic in top_topics:
            self.create_wordcloud(topic_slug=topic)
        
        # Create overall word cloud
        self.create_wordcloud()
        
        print("\n" + "=" * 80)
        print("All visualizations generated successfully!")
        print(f"Output directory: {self.output_dir}/")
        print("=" * 80)


def main():
    json_file = "backup-2025-11-14T03-19-14.json"
    
    visualizer = DataVisualizer(json_file)
    visualizer.generate_all_visualizations()


if __name__ == "__main__":
    main()


