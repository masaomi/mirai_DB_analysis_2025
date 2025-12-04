# Enhanced Survey Analysis - 高度なアンケート分析システム

## 概要

このシステムは、統計的手法（TF-IDF、クラスタリング）と感情分析を組み合わせて、アンケート回答を深く分析します。従来のキーワードベースの分類よりも精度が高く、「その他」カテゴリを大幅に削減できます。

## 主な機能

### 1. TF-IDF + クラスタリングによる自動カテゴリ化
- 回答の内容から重要キーワードを自動抽出
- K-meansクラスタリングで意味的に近い回答をグループ化
- 「その他」を最小化（従来の30-50% → 10%以下）

### 2. 感情分析
- 各回答を肯定的/否定的/中立に分類
- カテゴリごとの感情分布を可視化
- 感情に基づいた色分けチャート

### 3. 意図抽出
- 要望・希望のパターン検出
- 懸念・心配事項の識別
- 具体的な提案の抽出

### 4. 包括的なレポート生成
- Markdown形式の詳細レポート
- インタラクティブなHTML形式レポート
- カテゴリ別統計と代表的な回答
- 実用的なインサイトと推奨アクション

## ファイル構成

```
survey_analysis/
├── analyze_survey_enhanced.py    # メインスクリプト
├── sentiment_analyzer.py         # 感情分析モジュール
├── intent_extractor.py           # 意図抽出モジュール
├── enhanced_categorization.py    # TF-IDF + クラスタリング
├── enhanced_pie_charts.py        # 改善されたチャート生成
├── report_generator.py           # レポート生成
├── requirements.txt              # 必要なパッケージ
└── enhanced_results/             # 出力ディレクトリ
    └── enhanced_[slug]/
        ├── pie_chart.png         # 感情分析付きパイチャート
        ├── report.md             # Markdownレポート
        ├── report.html           # HTMLレポート
        └── analysis_data.json    # 分析データ
```

## セットアップ

### 1. 環境のアクティベート

```bash
conda activate mirai_db_analysis_py3.10
```

### 2. 必要なパッケージのインストール

```bash
cd survey_analysis
pip install -r requirements.txt
```

必要なパッケージ：
- scikit-learn (TF-IDF、クラスタリング)
- mecab-python3 (形態素解析)
- unidic-lite (MeCab辞書)
- matplotlib (グラフ作成)
- wordcloud (キーワード可視化)
- jinja2 (レポート生成)
- numpy, pandas

## 使い方

### 基本的な使い方

全アンケートを分析：
```bash
python analyze_survey_enhanced.py
```

特定のアンケートのみ分析：
```bash
python analyze_survey_enhanced.py [slug名]
```

### 例

```bash
# plan2026アンケートを分析
python analyze_survey_enhanced.py plan2026

# marumie-shikinアンケートを分析
python analyze_survey_enhanced.py marumie-shikin

# すべてのアンケートを分析
python analyze_survey_enhanced.py
```

## 出力ファイルの説明

### 1. pie_chart.png
- カテゴリ別回答分布のパイチャート
- 感情に基づいた色分け：
  - 緑：肯定的（60%以上）
  - 青：混合（40-60%）
  - グレー：中立
  - 赤：否定的（60%以上）
- カテゴリ別の詳細統計付き

### 2. report.md (Markdown形式)
- エグゼクティブサマリー
- 重要キーワード Top 10
- カテゴリ別詳細分析
  - 感情分析結果
  - 意図分析結果
  - 代表的な回答
  - 特徴的なキーワード
- インサイト
- 推奨アクション

### 3. report.html (HTML形式)
- Markdown版と同じ内容
- より見やすいビジュアルデザイン
- カラフルな感情分析バー
- ブラウザで直接開ける

### 4. analysis_data.json
- すべての分析結果の生データ
- プログラムで再利用可能
- カスタム分析に使用可能

## 従来の方法との比較

### 従来のキーワードベース方式（create_pie_charts.py）
- ✗ 固定的なキーワードマッチング
- ✗ 「その他」が30-50%
- ✗ アンケートごとに手動でキーワード設定が必要
- ✓ シンプルで高速

### 新しい統計的手法（analyze_survey_enhanced.py）
- ✓ データ駆動で自動的にカテゴリ発見
- ✓ 「その他」を10%以下に削減
- ✓ アンケート構造が変わっても自動適応
- ✓ 感情分析と意図抽出を含む
- ✓ 詳細なレポート生成
- ✗ 計算時間がやや長い（大規模データで数分）

## カスタマイズ

### クラスタ数の調整

`enhanced_categorization.py`の`EnhancedCategorizer`クラス：

```python
# デフォルト：自動決定
categorizer = EnhancedCategorizer(min_cluster_size=3)

# 手動でクラスタ数を指定
categories = categorizer.categorize_by_clustering(responses, n_clusters=5)
```

### 感情キーワードの追加

`sentiment_analyzer.py`の`SentimentAnalyzer`クラス：

```python
self.positive_keywords.add('新しいキーワード')
self.negative_keywords.add('新しいキーワード')
```

### 意図パターンの追加

`intent_extractor.py`の`IntentExtractor`クラス：

```python
self.intent_patterns['新しい意図'] = [
    r'パターン1',
    r'パターン2',
]
```

## トラブルシューティング

### MeCabのエラー
```
Error: MeCab initialization failed
```
→ unidic-liteが正しくインストールされているか確認してください。

### メモリエラー（大規模データ）
```
MemoryError: Unable to allocate array
```
→ 一度に処理するアンケート数を減らしてください（特定のslugを指定）。

### クラスタ数が適切でない
- `min_cluster_size`パラメータを調整
- 手動で`n_clusters`を指定

## 今後の改善案

1. **より高度な自然言語処理**
   - トピックモデリング（LDA）の導入
   - Word2Vec/BERTによる意味ベクトル化

2. **対話的な分析**
   - Streamlitダッシュボード
   - リアルタイムフィルタリング

3. **時系列分析**
   - 回答の時間変化を追跡
   - トレンド分析

4. **多言語対応**
   - 英語など他言語の回答にも対応

## 参考資料

- [scikit-learn Documentation](https://scikit-learn.org/)
- [MeCab Documentation](https://taku910.github.io/mecab/)
- [TF-IDF解説](https://ja.wikipedia.org/wiki/Tf-idf)
- [K-means クラスタリング](https://ja.wikipedia.org/wiki/K%E5%B9%B3%E5%9D%87%E6%B3%95)

## ライセンス

このプロジェクトのライセンスについては、プロジェクトルートのLICENSEファイルを参照してください。

## お問い合わせ

質問や改善提案がある場合は、イシューを作成してください。












