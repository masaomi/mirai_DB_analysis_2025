#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Survey Analysis Main Script
すべてのモジュールを統合したアンケート分析スクリプト
"""

import json
import os
import sys
from collections import defaultdict
from typing import Dict, List

# Import custom modules
from sentiment_analyzer import SentimentAnalyzer
from intent_extractor import IntentExtractor
from enhanced_categorization import EnhancedCategorizer
from enhanced_pie_charts import EnhancedPieChartGenerator
from report_generator import ReportGenerator


class EnhancedSurveyAnalyzer:
    """
    Enhanced survey analyzer integrating all modules
    """
    
    def __init__(self, json_file_path: str, output_dir: str):
        self.json_file_path = json_file_path
        self.output_dir = output_dir
        
        # Initialize modules
        self.sentiment_analyzer = SentimentAnalyzer()
        self.intent_extractor = IntentExtractor()
        self.categorizer = EnhancedCategorizer()
        self.chart_generator = EnhancedPieChartGenerator()
        self.report_generator = ReportGenerator()
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
    
    def load_data(self) -> Dict:
        """Load JSON data from file"""
        print(f"Loading data from {self.json_file_path}...")
        with open(self.json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print("Data loaded successfully.")
        return data
    
    def extract_survey_responses(self, data: Dict) -> Dict[str, List[Dict]]:
        """Extract survey responses grouped by slug"""
        print("Extracting survey responses...")
        
        sessions = data['tables']['interview_sessions']
        messages = data['tables']['messages']
        
        # Create session mappings
        session_slug_map = {}
        session_config_map = {}
        
        for session in sessions:
            session_id = session['id']
            slug = session['slug']
            config_title = session['config_title']
            session_slug_map[session_id] = slug
            session_config_map[session_id] = config_title
        
        # Collect responses by slug
        responses_by_slug = defaultdict(list)
        
        for message in messages:
            if message['role'] == 'user' and message['content']:
                session_id = message['session_id']
                content = message['content'].strip()
                
                # Filter out test responses and too short responses
                if len(content) < 3 or content.lower() in ['test', 'ああああ', 'a', 'aa', 'aaa']:
                    continue
                
                if session_id in session_slug_map:
                    slug = session_slug_map[session_id]
                    config_title = session_config_map.get(session_id, slug)
                    responses_by_slug[slug].append({
                        'content': content,
                        'session_id': session_id,
                        'config_title': config_title
                    })
        
        print(f"Extracted responses for {len(responses_by_slug)} different surveys.")
        for slug, responses in responses_by_slug.items():
            print(f"  - {slug}: {len(responses)} responses")
        
        return responses_by_slug
    
    def analyze_survey(self, slug: str, responses: List[Dict]) -> Dict:
        """
        Perform comprehensive analysis on a survey
        
        Args:
            slug: Survey slug
            responses: List of response dictionaries
            
        Returns:
            Analysis results dictionary
        """
        print(f"\n{'='*60}")
        print(f"Analyzing: {slug}")
        print(f"{'='*60}")
        
        if len(responses) < 3:
            print(f"Skipping {slug} - too few responses ({len(responses)})")
            return None
        
        config_title = responses[0]['config_title'] if responses else slug
        
        # Step 1: Extract top keywords using TF-IDF
        print("Step 1: Extracting key terms...")
        top_keywords = self.categorizer.extract_top_keywords(responses, n_keywords=20)
        print(f"  Found {len(top_keywords)} key terms")
        
        # Step 2: Categorize responses using clustering
        print("Step 2: Categorizing responses using clustering...")
        categories_raw = self.categorizer.categorize_by_clustering(responses)
        print(f"  Created {len(categories_raw)} categories")
        
        # Step 3: Analyze sentiment and intent for each category
        print("Step 3: Analyzing sentiment and intent...")
        categories = {}
        
        for category_name, category_responses in categories_raw.items():
            print(f"  Analyzing category: {category_name} ({len(category_responses)} responses)")
            
            # Sentiment analysis
            sentiments = [
                self.sentiment_analyzer.analyze(resp['content'])
                for resp in category_responses
            ]
            
            sentiment_counts = {
                'positive': sum(1 for s in sentiments if s['sentiment'] == 'positive'),
                'negative': sum(1 for s in sentiments if s['sentiment'] == 'negative'),
                'neutral': sum(1 for s in sentiments if s['sentiment'] == 'neutral'),
            }
            
            total_sentiment = sum(sentiment_counts.values())
            sentiment_pcts = {
                'positive_pct': (sentiment_counts['positive'] / total_sentiment * 100) if total_sentiment > 0 else 0,
                'negative_pct': (sentiment_counts['negative'] / total_sentiment * 100) if total_sentiment > 0 else 0,
                'neutral_pct': (sentiment_counts['neutral'] / total_sentiment * 100) if total_sentiment > 0 else 0,
            }
            
            # Intent analysis
            intents = [
                self.intent_extractor.extract_intent(resp['content'])
                for resp in category_responses
            ]
            
            intent_counts = {
                'desire_count': sum(1 for i in intents if i['has_desire']),
                'concern_count': sum(1 for i in intents if i['has_concern']),
                'proposal_count': sum(1 for i in intents if i['has_proposal']),
            }
            
            # Get sample responses (top 5)
            sample_responses = [resp['content'] for resp in category_responses[:5]]
            
            # Get keywords for this category
            category_keywords = []
            if category_responses and 'cluster_keywords' in category_responses[0]:
                category_keywords = category_responses[0]['cluster_keywords']
            
            categories[category_name] = {
                'responses': category_responses,
                'count': len(category_responses),
                'sentiment': {**sentiment_counts, **sentiment_pcts},
                'intent': intent_counts,
                'sample_responses': sample_responses,
                'keywords': category_keywords,
            }
        
        # Step 4: Calculate overall statistics
        print("Step 4: Calculating statistics...")
        
        all_topics = defaultdict(int)
        for resp in responses:
            intent_result = self.intent_extractor.extract_intent(resp['content'])
            for topic in intent_result['topics']:
                all_topics[topic] += 1
        
        top_topics = sorted(all_topics.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Generate summary
        total_responses = len(responses)
        largest_category = max(categories.items(), key=lambda x: x[1]['count'])
        largest_pct = (largest_category[1]['count'] / total_responses * 100)
        
        summary = f"このアンケートには{total_responses}件の回答があり、" \
                  f"{len(categories)}つのカテゴリに分類されました。" \
                  f"最も多いカテゴリは「{largest_category[0]}」で、" \
                  f"全体の{largest_pct:.1f}%を占めています。"
        
        analysis_result = {
            'slug': slug,
            'config_title': config_title,
            'total_responses': total_responses,
            'categories': categories,
            'top_keywords': top_keywords,
            'top_topics': top_topics,
            'summary': summary,
        }
        
        return analysis_result
    
    def generate_outputs(self, slug: str, analysis_result: Dict):
        """
        Generate all output files (charts and reports)
        
        Args:
            slug: Survey slug
            analysis_result: Analysis results
        """
        if not analysis_result:
            return
        
        config_title = analysis_result['config_title']
        
        # Create survey-specific output directory
        survey_dir = os.path.join(self.output_dir, f"enhanced_{slug}")
        os.makedirs(survey_dir, exist_ok=True)
        
        print(f"\nGenerating outputs for {slug}...")
        
        # Generate pie chart
        print("  - Creating pie chart...")
        chart_path = os.path.join(survey_dir, 'pie_chart.png')
        self.chart_generator.create_sentiment_pie_chart(
            analysis_result['categories'],
            f"{config_title}\n回答のカテゴリ分布（感情分析付き）",
            chart_path
        )
        
        # Generate Markdown report
        print("  - Creating Markdown report...")
        md_path = os.path.join(survey_dir, 'report.md')
        self.report_generator.generate_markdown_report(
            config_title,
            analysis_result,
            md_path
        )
        
        # Generate HTML report
        print("  - Creating HTML report...")
        html_path = os.path.join(survey_dir, 'report.html')
        self.report_generator.generate_html_report(
            config_title,
            analysis_result,
            html_path
        )
        
        # Save analysis data as JSON
        print("  - Saving analysis data...")
        json_path = os.path.join(survey_dir, 'analysis_data.json')
        
        # Prepare serializable data
        serializable_data = {
            'slug': analysis_result['slug'],
            'config_title': analysis_result['config_title'],
            'total_responses': analysis_result['total_responses'],
            'summary': analysis_result['summary'],
            'top_keywords': analysis_result['top_keywords'],
            'top_topics': analysis_result['top_topics'],
            'categories': {}
        }
        
        for cat_name, cat_data in analysis_result['categories'].items():
            serializable_data['categories'][cat_name] = {
                'count': cat_data['count'],
                'sentiment': cat_data['sentiment'],
                'intent': cat_data['intent'],
                'keywords': cat_data['keywords'],
                'sample_responses': cat_data['sample_responses'],
            }
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(serializable_data, f, ensure_ascii=False, indent=2)
        
        print(f"\nOutputs saved to: {survey_dir}")
        print(f"  - Chart: {chart_path}")
        print(f"  - Markdown Report: {md_path}")
        print(f"  - HTML Report: {html_path}")
        print(f"  - Analysis Data: {json_path}")
    
    def run_analysis(self, specific_slug: str = None):
        """
        Run the complete analysis pipeline
        
        Args:
            specific_slug: If provided, analyze only this survey
        """
        print("\n" + "="*60)
        print("Enhanced Survey Analysis")
        print("="*60 + "\n")
        
        # Load data
        data = self.load_data()
        
        # Extract responses
        responses_by_slug = self.extract_survey_responses(data)
        
        # Filter if specific slug is provided
        if specific_slug:
            if specific_slug in responses_by_slug:
                responses_by_slug = {specific_slug: responses_by_slug[specific_slug]}
            else:
                print(f"Error: Survey slug '{specific_slug}' not found")
                return
        
        # Analyze each survey
        results = {}
        for slug, responses in responses_by_slug.items():
            try:
                analysis_result = self.analyze_survey(slug, responses)
                if analysis_result:
                    results[slug] = analysis_result
                    self.generate_outputs(slug, analysis_result)
            except Exception as e:
                print(f"Error analyzing {slug}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        print("\n" + "="*60)
        print(f"Analysis complete! Analyzed {len(results)} surveys.")
        print(f"Results saved to: {self.output_dir}")
        print("="*60 + "\n")
        
        return results


def main():
    """Main function"""
    # Configuration
    json_file = '/Users/masa/forback/github/mirai_DB_backup/backup-2025-11-14T03-19-14.json'
    output_dir = '/Users/masa/forback/github/mirai_DB_backup/survey_analysis/enhanced_results'
    
    # Parse command line arguments
    specific_slug = None
    if len(sys.argv) > 1:
        specific_slug = sys.argv[1]
        print(f"Analyzing specific survey: {specific_slug}")
    
    # Create analyzer
    analyzer = EnhancedSurveyAnalyzer(json_file, output_dir)
    
    # Run analysis
    analyzer.run_analysis(specific_slug)


if __name__ == '__main__':
    main()












