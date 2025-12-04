#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
アンケート回答のカテゴリ化とパイチャート作成スクリプト
"""

import json
import matplotlib.pyplot as plt
from collections import defaultdict, Counter
import os
from datetime import datetime

# 日本語フォント設定
plt.rcParams['font.sans-serif'] = ['Hiragino Sans', 'Yu Gothic', 'Meiryo', 'MS Gothic', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

def load_json_data(file_path):
    """JSONデータを読み込む"""
    print(f"Loading JSON data from {file_path}...")
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print("JSON data loaded successfully.")
    return data

def extract_survey_responses(data):
    """アンケートの回答を抽出する"""
    print("Extracting survey responses...")
    
    # セッション情報を取得
    sessions = data['tables']['interview_sessions']
    messages = data['tables']['messages']
    
    # session_idとslugのマッピングを作成
    session_slug_map = {}
    session_config_map = {}
    for session in sessions:
        session_id = session['id']
        slug = session['slug']
        config_title = session['config_title']
        session_slug_map[session_id] = slug
        session_config_map[session_id] = config_title
    
    # slug別に回答を収集
    responses_by_slug = defaultdict(list)
    
    for message in messages:
        if message['role'] == 'user' and message['content']:
            session_id = message['session_id']
            content = message['content'].strip()
            
            # テスト回答や短すぎる回答を除外
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

def categorize_responses_simple(responses):
    """
    回答を簡単なルールベースでカテゴリ化する
    より高度な分析にはLLM APIを使用することも可能
    """
    categories = defaultdict(list)
    
    for resp in responses:
        content = resp['content'].lower()
        
        # キーワードベースの簡単なカテゴリ化
        # 政治・政策関連
        if any(word in content for word in ['政治', '政策', '議員', '国会', '選挙', '投票', '法案', '政権']):
            categories['政治・政策関連'].append(resp)
        # 透明性・情報公開
        elif any(word in content for word in ['透明', '公開', '見える', '可視化', 'dx', 'デジタル', 'システム']):
            categories['透明性・情報公開'].append(resp)
        # 課題・問題点
        elif any(word in content for word in ['課題', '問題', '懸念', '心配', '不安', 'リスク', '反対']):
            categories['課題・懸念'].append(resp)
        # 期待・要望
        elif any(word in content for word in ['期待', '希望', '願', 'してほしい', 'したい', '賛成', '良い']):
            categories['期待・要望'].append(resp)
        # 具体的な提案
        elif any(word in content for word in ['提案', '実現', '推進', '取り組', '必要', 'すべき', '改善']):
            categories['具体的な提案'].append(resp)
        # その他
        else:
            categories['その他'].append(resp)
    
    return categories

def categorize_by_topic(responses, slug):
    """
    アンケートの種類に応じてより詳細にカテゴリ化する
    """
    if 'plan2026' in slug:
        # チームみらいの1年プラン関連
        categories = defaultdict(list)
        for resp in responses:
            content = resp['content'].lower()
            
            if any(word in content for word in ['議席', '選挙', '候補', '当選']):
                categories['選挙・議席獲得'].append(resp)
            elif any(word in content for word in ['dx', 'デジタル', 'システム', 'it', 'オンライン', 'web']):
                categories['DX・デジタル化'].append(resp)
            elif any(word in content for word in ['透明', '公開', '見える', '可視化', '情報']):
                categories['透明性・情報公開'].append(resp)
            elif any(word in content for word in ['政治資金', '献金', 'お金', '資金', '財務']):
                categories['政治資金の透明化'].append(resp)
            elif any(word in content for word in ['汚職', '不正', '腐敗', '癒着']):
                categories['汚職・不正の撲滅'].append(resp)
            elif any(word in content for word in ['国民', '庶民', '市民', '生活', '暮らし']):
                categories['国民生活の改善'].append(resp)
            elif any(word in content for word in ['平和', '戦争', '防衛', '安全保障']):
                categories['平和・安全保障'].append(resp)
            else:
                categories['その他の意見'].append(resp)
                
    elif 'bill-of-lading' in slug:
        # 船荷証券の電子化関連
        categories = defaultdict(list)
        for resp in responses:
            content = resp['content'].lower()
            
            if any(word in content for word in ['賛成', '良い', 'メリット', '効率', '便利']):
                categories['賛成・肯定的'].append(resp)
            elif any(word in content for word in ['反対', '懸念', '心配', 'リスク', 'デメリット']):
                categories['反対・否定的'].append(resp)
            elif any(word in content for word in ['セキュリティ', 'security', '安全', '保護', '暗号']):
                categories['セキュリティ関連'].append(resp)
            elif any(word in content for word in ['コスト', '費用', '経費', 'お金']):
                categories['コスト関連'].append(resp)
            elif any(word in content for word in ['実務', '実装', '運用', '導入', '手続き']):
                categories['実務・運用面'].append(resp)
            else:
                categories['その他'].append(resp)
    else:
        # デフォルトのカテゴリ化
        categories = categorize_responses_simple(responses)
    
    return categories

def create_pie_chart(categories, title, output_path):
    """カテゴリ別のパイチャートを作成"""
    if not categories:
        print(f"No data to create pie chart for: {title}")
        return
    
    # カテゴリとカウントを準備
    labels = []
    sizes = []
    for category, responses in sorted(categories.items(), key=lambda x: len(x[1]), reverse=True):
        labels.append(f"{category}\n({len(responses)}件)")
        sizes.append(len(responses))
    
    # パイチャート作成
    fig, ax = plt.subplots(figsize=(12, 8))
    colors = plt.cm.Set3(range(len(labels)))
    
    wedges, texts, autotexts = ax.pie(
        sizes,
        labels=labels,
        colors=colors,
        autopct='%1.1f%%',
        startangle=90,
        textprops={'fontsize': 10}
    )
    
    # フォントサイズ調整
    for text in texts:
        text.set_fontsize(11)
    for autotext in autotexts:
        autotext.set_fontsize(9)
        autotext.set_color('black')
        autotext.set_weight('bold')
    
    ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
    plt.tight_layout()
    
    # 保存
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Saved pie chart: {output_path}")
    plt.close()

def main():
    # 設定
    json_file = '/Users/masa/forback/github/mirai_DB_backup/backup-2025-11-14T03-19-14.json'
    output_dir = '/Users/masa/forback/github/mirai_DB_backup/survey_analysis'
    
    # 出力ディレクトリ作成
    os.makedirs(output_dir, exist_ok=True)
    
    # データ読み込み
    data = load_json_data(json_file)
    
    # 回答抽出
    responses_by_slug = extract_survey_responses(data)
    
    # 各アンケートについてカテゴリ化とパイチャート作成
    for slug, responses in responses_by_slug.items():
        if len(responses) < 5:  # 回答が少なすぎる場合はスキップ
            print(f"Skipping {slug} (too few responses: {len(responses)})")
            continue
        
        print(f"\n--- Analyzing: {slug} ---")
        
        # カテゴリ化
        categories = categorize_by_topic(responses, slug)
        
        # カテゴリ情報を表示
        print(f"Categories for {slug}:")
        for category, cat_responses in sorted(categories.items(), key=lambda x: len(x[1]), reverse=True):
            print(f"  {category}: {len(cat_responses)} responses")
        
        # 回答例を表示（各カテゴリから最大3件）
        print(f"\nSample responses for {slug}:")
        for category, cat_responses in sorted(categories.items(), key=lambda x: len(x[1]), reverse=True):
            print(f"\n  [{category}]:")
            for resp in cat_responses[:3]:
                preview = resp['content'][:100] + '...' if len(resp['content']) > 100 else resp['content']
                print(f"    - {preview}")
        
        # パイチャート作成
        config_title = responses[0]['config_title'] if responses else slug
        output_path = os.path.join(output_dir, f'pie_chart_{slug}.png')
        create_pie_chart(categories, f'{config_title}\n回答のカテゴリ分布', output_path)
    
    print(f"\n=== Analysis complete ===")
    print(f"Output directory: {output_dir}")

if __name__ == '__main__':
    main()



