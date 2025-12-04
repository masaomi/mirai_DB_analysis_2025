#!/usr/bin/env python3
"""
AIアンケートデータの多角的解析スクリプト

このスクリプトは、自由記述式アンケートデータを以下の観点から解析します：
1. データの基本統計
2. トピック別の分析
3. テキスト分析（感情分析、キーワード抽出）
4. カテゴリ化の提案
5. ビジュアル化の準備
"""

import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from typing import Dict, List, Any
import sys

class SurveyDataAnalyzer:
    def __init__(self, json_file_path: str):
        """Initialize analyzer with JSON backup file"""
        print(f"Loading data from {json_file_path}...")
        with open(json_file_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        self.tables = self.data['tables']
        print("Data loaded successfully!")
        
    def get_basic_stats(self) -> Dict[str, Any]:
        """Get basic statistics about the data"""
        stats = {
            'timestamp': self.data.get('timestamp'),
            'tables': {}
        }
        
        for table_name, records in self.tables.items():
            stats['tables'][table_name] = {
                'count': len(records),
                'sample_keys': list(records[0].keys()) if records else []
            }
        
        return stats
    
    def analyze_interview_topics(self) -> Dict[str, Any]:
        """Analyze interview topics and their distribution"""
        configs = self.tables['interview_configs']
        sessions = self.tables['interview_sessions']
        messages = self.tables['messages']
        
        # Topic distribution
        topic_stats = {}
        for config in configs:
            topic_id = config['id']
            slug = config.get('slug', 'unknown')
            title = config.get('title', 'Unknown')
            
            # Count sessions per topic
            topic_sessions = [s for s in sessions if s.get('slug') == slug]
            
            # Count user messages (responses) per topic
            session_ids = {s['id'] for s in topic_sessions}
            topic_messages = [m for m in messages 
                            if m.get('session_id') in session_ids 
                            and m.get('role') == 'user']
            
            topic_stats[slug] = {
                'id': topic_id,
                'title': title,
                'sessions_count': len(topic_sessions),
                'user_responses_count': len(topic_messages),
                'avg_responses_per_session': len(topic_messages) / len(topic_sessions) if topic_sessions else 0
            }
        
        return topic_stats
    
    def analyze_text_lengths(self) -> Dict[str, Any]:
        """Analyze text length distribution of user responses"""
        messages = self.tables['messages']
        user_messages = [m for m in messages if m.get('role') == 'user']
        
        lengths = [len(m.get('content', '')) for m in user_messages]
        
        if not lengths:
            return {}
        
        return {
            'total_responses': len(lengths),
            'min_length': min(lengths),
            'max_length': max(lengths),
            'avg_length': sum(lengths) / len(lengths),
            'median_length': sorted(lengths)[len(lengths) // 2],
            'length_distribution': {
                'short (0-50 chars)': len([l for l in lengths if l <= 50]),
                'medium (51-200 chars)': len([l for l in lengths if 50 < l <= 200]),
                'long (201-500 chars)': len([l for l in lengths if 200 < l <= 500]),
                'very_long (500+ chars)': len([l for l in lengths if l > 500])
            }
        }
    
    def extract_keywords(self, top_n: int = 50) -> Dict[str, List[str]]:
        """Extract common keywords from user responses"""
        messages = self.tables['messages']
        user_messages = [m.get('content', '') for m in messages if m.get('role') == 'user']
        
        # Simple keyword extraction (can be enhanced with NLP libraries)
        all_words = []
        for content in user_messages:
            if content:
                # Remove punctuation and split
                words = re.findall(r'\w+', content.lower())
                # Filter out very short words and common stop words
                stop_words = {'の', 'に', 'は', 'を', 'が', 'と', 'で', 'も', 'から', 'など', 
                             'て', 'に', 'は', 'を', 'が', 'と', 'で', 'も', 'から', 'など',
                             'this', 'that', 'the', 'a', 'an', 'is', 'are', 'was', 'were'}
                words = [w for w in words if len(w) > 1 and w not in stop_words]
                all_words.extend(words)
        
        word_freq = Counter(all_words)
        top_keywords = [word for word, count in word_freq.most_common(top_n)]
        
        return {
            'top_keywords': top_keywords,
            'total_unique_words': len(word_freq),
            'keyword_frequencies': dict(word_freq.most_common(top_n))
        }
    
    def analyze_by_topic(self, topic_slug: str) -> Dict[str, Any]:
        """Analyze responses for a specific topic"""
        sessions = self.tables['interview_sessions']
        messages = self.tables['messages']
        
        topic_sessions = [s for s in sessions if s.get('slug') == topic_slug]
        session_ids = {s['id'] for s in topic_sessions}
        
        topic_messages = [m for m in messages 
                         if m.get('session_id') in session_ids 
                         and m.get('role') == 'user']
        
        response_lengths = [len(m.get('content', '')) for m in topic_messages]
        
        return {
            'topic': topic_slug,
            'sessions': len(topic_sessions),
            'responses': len(topic_messages),
            'avg_response_length': sum(response_lengths) / len(response_lengths) if response_lengths else 0,
            'sample_responses': [m.get('content', '')[:200] for m in topic_messages[:5]]
        }
    
    def get_session_reports_summary(self) -> Dict[str, Any]:
        """Analyze aggregate reports and session reports"""
        sessions = self.tables['interview_sessions']
        reports = self.tables.get('aggregate_reports', [])
        
        completed_sessions = [s for s in sessions if s.get('status') == 'completed']
        sessions_with_reports = [s for s in completed_sessions if s.get('report')]
        
        return {
            'total_sessions': len(sessions),
            'completed_sessions': len(completed_sessions),
            'sessions_with_reports': len(sessions_with_reports),
            'aggregate_reports': len(reports),
            'completion_rate': len(completed_sessions) / len(sessions) if sessions else 0
        }
    
    def generate_analysis_report(self) -> str:
        """Generate a comprehensive analysis report"""
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("AIアンケートデータ解析レポート")
        report_lines.append("=" * 80)
        report_lines.append("")
        
        # Basic stats
        report_lines.append("## 基本統計")
        report_lines.append("-" * 80)
        stats = self.get_basic_stats()
        report_lines.append(f"バックアップ作成日時: {stats['timestamp']}")
        report_lines.append("")
        report_lines.append("テーブル別レコード数:")
        for table_name, table_info in stats['tables'].items():
            report_lines.append(f"  - {table_name}: {table_info['count']:,} 件")
        report_lines.append("")
        
        # Topic analysis
        report_lines.append("## トピック別分析")
        report_lines.append("-" * 80)
        topic_stats = self.analyze_interview_topics()
        for slug, stats in sorted(topic_stats.items(), key=lambda x: x[1]['sessions_count'], reverse=True):
            report_lines.append(f"\n### {stats['title']} ({slug})")
            report_lines.append(f"  - セッション数: {stats['sessions_count']:,}")
            report_lines.append(f"  - ユーザー回答数: {stats['user_responses_count']:,}")
            report_lines.append(f"  - セッションあたりの平均回答数: {stats['avg_responses_per_session']:.1f}")
        report_lines.append("")
        
        # Text length analysis
        report_lines.append("## 回答テキスト長の分析")
        report_lines.append("-" * 80)
        length_stats = self.analyze_text_lengths()
        if length_stats:
            report_lines.append(f"総回答数: {length_stats['total_responses']:,}")
            report_lines.append(f"平均文字数: {length_stats['avg_length']:.1f}")
            report_lines.append(f"中央値: {length_stats['median_length']}")
            report_lines.append(f"最小: {length_stats['min_length']}, 最大: {length_stats['max_length']}")
            report_lines.append("\n文字数分布:")
            for category, count in length_stats['length_distribution'].items():
                percentage = (count / length_stats['total_responses']) * 100
                report_lines.append(f"  - {category}: {count:,} ({percentage:.1f}%)")
        report_lines.append("")
        
        # Keywords
        report_lines.append("## 頻出キーワード（上位20）")
        report_lines.append("-" * 80)
        keywords = self.extract_keywords(top_n=20)
        if keywords.get('keyword_frequencies'):
            for word, freq in list(keywords['keyword_frequencies'].items())[:20]:
                report_lines.append(f"  - {word}: {freq}回")
        report_lines.append("")
        
        # Session reports
        report_lines.append("## セッションレポート分析")
        report_lines.append("-" * 80)
        report_stats = self.get_session_reports_summary()
        report_lines.append(f"総セッション数: {report_stats['total_sessions']:,}")
        report_lines.append(f"完了セッション数: {report_stats['completed_sessions']:,}")
        report_lines.append(f"レポート付きセッション数: {report_stats['sessions_with_reports']:,}")
        report_lines.append(f"完了率: {report_stats['completion_rate']*100:.1f}%")
        report_lines.append(f"集計レポート数: {report_stats['aggregate_reports']}")
        report_lines.append("")
        
        # Analysis recommendations
        report_lines.append("## 推奨される解析方法")
        report_lines.append("-" * 80)
        report_lines.append("""
1. **カテゴリ化分析**
   - トピックごとの回答をクラスタリング
   - 感情分析によるポジティブ/ネガティブ分類
   - テーマ別の自動分類（例：メリット、懸念、提案など）

2. **ビジュアル化**
   - トピック別の回答数・セッション数の棒グラフ
   - 回答文字数の分布ヒストグラム
   - キーワードのワードクラウド
   - 時系列での回答数の推移
   - セッション完了率の可視化

3. **深掘り分析**
   - トピック間の回答パターンの比較
   - 長文回答と短文回答の内容の違い
   - セッションの完了率と回答品質の関係

4. **AIエージェントによる議論**
   - 過去の有名人（例：政治家、思想家）のAIエージェントを召喚
   - 各トピックの回答を彼らの視点で分析・議論
   - 異なる立場からの意見の対比

5. **テキストマイニング**
   - 共起ネットワーク分析（キーワードの関連性）
   - トピックモデリング（LDA等）
   - 感情分析（ポジティブ/ネガティブ/ニュートラル）
   - 要約生成（各トピックの主要な意見の抽出）
        """)
        
        return "\n".join(report_lines)


def main():
    json_file = "backup-2025-11-14T03-19-14.json"
    
    print("Initializing analyzer...")
    analyzer = SurveyDataAnalyzer(json_file)
    
    print("\nGenerating analysis report...")
    report = analyzer.generate_analysis_report()
    
    # Print to console
    print(report)
    
    # Save to file
    output_file = "analysis_report.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"\n\nReport saved to {output_file}")


if __name__ == "__main__":
    main()


