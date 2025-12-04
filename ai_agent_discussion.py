#!/usr/bin/env python3
"""
AIエージェントによる議論スクリプト

過去の有名人のAIエージェントを召喚し、アンケート回答を分析・議論させます
"""

import json
from typing import Dict, List, Any, Optional
from collections import defaultdict
import sys


class AIAgentDiscussion:
    def __init__(self, json_file_path: str):
        """Initialize with survey data"""
        print(f"Loading data from {json_file_path}...")
        with open(json_file_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        self.tables = self.data['tables']
        print("Data loaded successfully!")
        
        # Define historical figures and their perspectives
        self.agents = {
            'plato': {
                'name': 'プラトン',
                'description': '古代ギリシャの哲学者。正義、理想国家、教育について深い洞察を持つ。',
                'perspective': '正義と理想的な社会秩序の観点から分析する',
                'focus': ['正義', '理想', '教育', '統治', '哲学']
            },
            'confucius': {
                'name': '孔子',
                'description': '中国の思想家。道徳、礼、仁について説いた。',
                'perspective': '道徳と社会秩序の観点から分析する',
                'focus': ['道徳', '礼', '仁', '社会秩序', '統治']
            },
            'machiavelli': {
                'name': 'マキャベリ',
                'description': 'イタリアの政治思想家。現実主義的な政治理論で知られる。',
                'perspective': '権力と統治の実効性の観点から分析する',
                'focus': ['権力', '統治', '実効性', '現実主義', '政治']
            },
            'rousseau': {
                'name': 'ルソー',
                'description': 'フランスの哲学者。社会契約論、一般意志について論じた。',
                'perspective': '社会契約と一般意志の観点から分析する',
                'focus': ['社会契約', '一般意志', '自由', '平等', '民主主義']
            },
            'mill': {
                'name': 'ジョン・スチュアート・ミル',
                'description': 'イギリスの哲学者・経済学者。自由主義、功利主義を論じた。',
                'perspective': '個人の自由と最大多数の最大幸福の観点から分析する',
                'focus': ['自由', '功利主義', '個人の権利', '最大幸福', '自由主義']
            },
            'fukuzawa': {
                'name': '福澤諭吉',
                'description': '日本の啓蒙思想家。独立自尊、実学を重視した。',
                'perspective': '日本の近代化と独立自尊の観点から分析する',
                'focus': ['独立自尊', '実学', '近代化', '教育', '日本の発展']
            },
            'ozaki': {
                'name': '尾崎行雄',
                'description': '日本の政治家。「憲政の神様」と呼ばれた。議会政治を重視。',
                'perspective': '議会政治と民主主義の観点から分析する',
                'focus': ['議会政治', '民主主義', '憲政', '政治改革', '透明性']
            }
        }
    
    def extract_topic_responses(self, topic_slug: str, max_responses: int = 100) -> List[Dict[str, Any]]:
        """Extract responses for a topic"""
        sessions = self.tables['interview_sessions']
        messages = self.tables['messages']
        
        topic_sessions = [s for s in sessions if s.get('slug') == topic_slug]
        session_ids = {s['id'] for s in topic_sessions}
        
        responses = []
        for m in messages:
            if m.get('session_id') in session_ids and m.get('role') == 'user':
                content = m.get('content', '').strip()
                if content and len(content) > 10:  # Filter very short responses
                    responses.append({
                        'content': content,
                        'session_id': m.get('session_id'),
                        'timestamp': m.get('timestamp')
                    })
                    if len(responses) >= max_responses:
                        break
        
        return responses
    
    def summarize_responses(self, responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create a summary of responses for discussion"""
        if not responses:
            return {}
        
        # Group by length
        short_responses = [r for r in responses if len(r['content']) <= 100]
        medium_responses = [r for r in responses if 100 < len(r['content']) <= 500]
        long_responses = [r for r in responses if len(r['content']) > 500]
        
        # Sample responses
        sample_short = [r['content'] for r in short_responses[:5]]
        sample_medium = [r['content'] for r in medium_responses[:5]]
        sample_long = [r['content'] for r in long_responses[:3]]
        
        return {
            'total': len(responses),
            'short_count': len(short_responses),
            'medium_count': len(medium_responses),
            'long_count': len(long_responses),
            'sample_short': sample_short,
            'sample_medium': sample_medium,
            'sample_long': sample_long,
            'all_responses': [r['content'] for r in responses[:20]]  # First 20 for context
        }
    
    def generate_agent_prompt(self, agent_key: str, topic_title: str, summary: Dict[str, Any]) -> str:
        """Generate a prompt for an AI agent"""
        agent = self.agents[agent_key]
        
        prompt = f"""あなたは{agent['name']}（{agent['description']}）のAIエージェントです。

以下のアンケート回答データを、{agent['perspective']}観点から分析・議論してください。

【トピック】{topic_title}

【回答データの概要】
- 総回答数: {summary['total']}
- 短文回答（100文字以下）: {summary['short_count']}件
- 中程度の回答（101-500文字）: {summary['medium_count']}件
- 長文回答（500文字超）: {summary['long_count']}件

【回答サンプル】

短文回答の例:
"""
        
        for i, resp in enumerate(summary['sample_short'][:3], 1):
            prompt += f"{i}. {resp}\n"
        
        prompt += "\n中程度の回答の例:\n"
        for i, resp in enumerate(summary['sample_medium'][:3], 1):
            prompt += f"{i}. {resp}\n"
        
        if summary['sample_long']:
            prompt += "\n長文回答の例:\n"
            for i, resp in enumerate(summary['sample_long'][:2], 1):
                prompt += f"{i}. {resp[:500]}...\n"
        
        prompt += f"""
【分析の観点】
{agent['perspective']}
特に以下の点に注目してください: {', '.join(agent['focus'])}

【回答の形式】
1. 回答データの全体的な印象
2. あなたの思想・理論の観点からの分析
3. 重要な洞察や気づき
4. 他の視点との対比（もしあれば）
5. 今後の展望や提言

{agent['name']}として、率直で深い洞察を提供してください。
"""
        
        return prompt
    
    def prepare_discussion_data(self, topic_slug: str, topic_title: str, 
                                agent_keys: List[str] = None) -> Dict[str, Any]:
        """Prepare data for multi-agent discussion"""
        if agent_keys is None:
            agent_keys = ['plato', 'confucius', 'machiavelli', 'rousseau', 'mill']
        
        print(f"\nPreparing discussion data for topic: {topic_title}")
        print("-" * 80)
        
        responses = self.extract_topic_responses(topic_slug, max_responses=100)
        summary = self.summarize_responses(responses)
        
        if not summary:
            print("No responses found for this topic")
            return {}
        
        print(f"Extracted {summary['total']} responses")
        
        # Generate prompts for each agent
        agent_prompts = {}
        for agent_key in agent_keys:
            if agent_key in self.agents:
                prompt = self.generate_agent_prompt(agent_key, topic_title, summary)
                agent_prompts[agent_key] = {
                    'agent_info': self.agents[agent_key],
                    'prompt': prompt
                }
        
        return {
            'topic': topic_slug,
            'topic_title': topic_title,
            'summary': summary,
            'agent_prompts': agent_prompts
        }
    
    def save_discussion_prompts(self, discussion_data: Dict[str, Any], output_file: str):
        """Save discussion prompts to a file"""
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write(f"AIエージェント議論用プロンプト\n")
            f.write(f"トピック: {discussion_data['topic_title']}\n")
            f.write("=" * 80 + "\n\n")
            
            f.write("## 回答データの概要\n")
            f.write("-" * 80 + "\n")
            summary = discussion_data['summary']
            f.write(f"総回答数: {summary['total']}\n")
            f.write(f"短文回答: {summary['short_count']}件\n")
            f.write(f"中程度の回答: {summary['medium_count']}件\n")
            f.write(f"長文回答: {summary['long_count']}件\n\n")
            
            f.write("## 各エージェントへのプロンプト\n")
            f.write("-" * 80 + "\n\n")
            
            for agent_key, agent_data in discussion_data['agent_prompts'].items():
                agent_info = agent_data['agent_info']
                f.write(f"### {agent_info['name']}\n")
                f.write(f"説明: {agent_info['description']}\n")
                f.write(f"観点: {agent_info['perspective']}\n\n")
                f.write("プロンプト:\n")
                f.write(agent_data['prompt'])
                f.write("\n" + "-" * 80 + "\n\n")
        
        print(f"Discussion prompts saved to: {output_file}")


def main():
    json_file = "backup-2025-11-14T03-19-14.json"
    
    discussion = AIAgentDiscussion(json_file)
    
    # Get topic info
    configs = discussion.tables['interview_configs']
    sessions = discussion.tables['interview_sessions']
    
    # Find top topic
    topic_counts = Counter(s.get('slug') for s in sessions if s.get('slug'))
    top_topic_slug = topic_counts.most_common(1)[0][0]
    
    # Get topic title
    topic_title = "Unknown"
    for config in configs:
        if config.get('slug') == top_topic_slug:
            topic_title = config.get('title', 'Unknown')
            break
    
    print(f"\nPreparing discussion for top topic: {topic_title} ({top_topic_slug})")
    
    # Prepare discussion data
    discussion_data = discussion.prepare_discussion_data(
        top_topic_slug, 
        topic_title,
        agent_keys=['plato', 'confucius', 'machiavelli', 'rousseau', 'mill', 'fukuzawa', 'ozaki']
    )
    
    if discussion_data:
        # Save prompts
        output_file = f"discussion_prompts_{top_topic_slug}.txt"
        discussion.save_discussion_prompts(discussion_data, output_file)
        
        print("\n" + "=" * 80)
        print("Discussion prompts generated successfully!")
        print("=" * 80)
        print("\nYou can now use these prompts with AI models to generate")
        print("discussions from different historical perspectives.")


if __name__ == "__main__":
    from collections import Counter
    main()


