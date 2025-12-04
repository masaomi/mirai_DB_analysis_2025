# Survey Summary Generation - ガイド

RAG DBに基づいて各アンケートトピックの要約をLLMで生成し、HTML形式で出力するツールです。

## 🎯 機能

- **各アンケートトピックごとに独立したHTML要約を生成**
- **包括的な統計情報を含む**（感情分析、品質分布、キーワード統計など）
- **LLM選択可能**（デフォルト: Ollama gpt-oss:20b）
- **見やすいHTML形式**（グラフ、表、カラフルなデザイン）
- **インデックスページ自動生成**（全トピックの一覧）

## 📋 前提条件

1. ChromaDBが作成済み（`./chroma_db` ディレクトリが存在）
2. Conda環境 `mirai_db_analysis_py3.11` がアクティブ
3. LLMサービスが利用可能
   - **Ollama**: ローカルで `ollama serve` が実行中
   - **AWS Bedrock**: AWS認証情報が設定済み

## 🚀 基本的な使い方

### 方法1: スクリプトで実行（推奨）

```bash
cd /Users/masa/forback/github/mirai_DB_backup/survey_rag_app
./generate_summaries.sh
```

### 方法2: Pythonスクリプトを直接実行

```bash
conda activate mirai_db_analysis_py3.11
cd /Users/masa/forback/github/mirai_DB_backup/survey_rag_app
python generate_survey_summaries.py
```

## 🔧 詳細なオプション

### Ollama使用（デフォルト）

```bash
python generate_survey_summaries.py \
  --provider ollama \
  --ollama-model gpt-oss:20b \
  --ollama-base-url http://localhost:11434
```

### AWS Bedrock使用

```bash
python generate_survey_summaries.py \
  --provider bedrock \
  --bedrock-region us-east-1 \
  --bedrock-model anthropic.claude-3-5-sonnet-20240620-v1:0
```

AWS Profileを指定する場合：

```bash
python generate_survey_summaries.py \
  --provider bedrock \
  --bedrock-profile your-profile-name
```

### 特定のトピックのみ処理

```bash
python generate_survey_summaries.py \
  --topics marumie-shikin-user mirai-gikai-interview
```

### 出力ディレクトリの変更

```bash
python generate_survey_summaries.py \
  --output-dir ./my_summaries
```

### 1トピックあたりの最大ドキュメント数を指定

```bash
python generate_survey_summaries.py \
  --max-docs 200
```

## 📊 生成されるファイル

### ディレクトリ構造

```
survey_summaries_html/
├── index.html                    # 全トピックの一覧ページ
├── marumie-shikin-user.html      # トピック1の要約
├── mirai-gikai-interview.html    # トピック2の要約
├── plan2026-public.html          # トピック3の要約
└── ...                           # その他のトピック
```

### 各HTMLファイルの内容

1. **ヘッダー**
   - トピック名
   - 生成日時
   - LLMプロバイダー情報

2. **統計情報**
   - 総回答数
   - 平均感情スコア
   - 期間
   - 感情分布（表）
   - 品質分布（表）
   - キーワード統計

3. **LLM生成の要約レポート**
   - 概要サマリー
   - 主要な発見事項
   - 感情分析
   - 主要な意見・テーマ
   - 注目すべき個別意見
   - 結論と示唆

## 📝 生成される要約の構造

LLMは以下の構成で要約を生成します：

### 1. 概要サマリー（2-3段落）
- アンケートの主要な目的と背景
- 全体的な傾向と回答の特徴

### 2. 主要な発見事項（箇条書き）
- 最も重要な3-5つの発見
- 具体的な回答例を引用

### 3. 感情分析
- 回答者の全体的な感情傾向
- ポジティブ・ネガティブ意見の内訳

### 4. 主要な意見・テーマ
- 繰り返し現れるテーマやトピック
- 代表的な意見グループ

### 5. 注目すべき個別意見
- 特に印象的だった回答
- ユニークな視点や提案

### 6. 結論と示唆
- データから得られる洞察
- 今後の対応や検討事項の提案

## 🎨 HTMLデザイン

- **レスポンシブデザイン**: モバイル・デスクトップ対応
- **カラフルな統計カード**: 重要な指標を視覚的に表示
- **テーブル**: 詳細な分布データ
- **プリントフレンドリー**: 印刷時に適切なレイアウト
- **グラデーションヘッダー**: 視覚的に魅力的

## ⏱️ 処理時間の目安

- **1トピックあたり**: 30秒〜2分（LLMの速度による）
- **15トピック**: 約10〜30分
- **Ollama (ローカル)**: 高速だがマシンスペック依存
- **AWS Bedrock**: 安定しているがAPI制限に注意

## 🔍 結果の確認

### インデックスページを開く

```bash
open survey_summaries_html/index.html
```

または：

```bash
cd survey_summaries_html
python -m http.server 8000
# ブラウザで http://localhost:8000 を開く
```

### 個別ファイルを開く

```bash
open survey_summaries_html/marumie-shikin-user.html
```

## 🐛 トラブルシューティング

### "ChromaDB not found"

```bash
./ingest.sh
```

を実行してDBを作成してください。

### Ollama接続エラー

```bash
# Ollamaが起動しているか確認
curl http://localhost:11434/api/tags

# 起動していない場合
ollama serve

# モデルがpullされているか確認
ollama list

# モデルをpull
ollama pull gpt-oss:20b
```

### AWS Bedrock認証エラー

```bash
# AWS認証情報を確認
aws configure list

# 再設定
aws configure
```

### メモリ不足エラー

```bash
# 1トピックあたりのドキュメント数を減らす
python generate_survey_summaries.py --max-docs 50
```

### LLMタイムアウト

LLMの応答が遅い場合：
1. より小さいモデルを使用
2. `--max-docs` を減らして処理するデータ量を削減
3. インターネット接続を確認（Bedrockの場合）

## 📊 統計情報について

各HTMLには以下の統計が含まれます：

### 基本統計
- **総回答数**: そのトピックの総回答数
- **平均感情スコア**: -1（ネガティブ）〜 +1（ポジティブ）
- **期間**: 最初と最後の回答日

### 感情分布
- positive: 明確にポジティブ
- slightly_positive: ややポジティブ
- neutral: 中立
- slightly_negative: ややネガティブ
- negative: 明確にネガティブ
- unknown: 判定不能

### 品質分布
- high: 高品質（長く、構造的）
- medium: 中品質
- low: 低品質
- very_low: 非常に低品質

### キーワード統計
- ポジティブキーワード: 賛成、良い、期待など
- ネガティブキーワード: 反対、問題、懸念など
- 政策関連キーワード: 法案、政策、制度など

## 🔄 再生成

既に生成したレポートを再生成する場合：

```bash
# 出力ディレクトリを削除
rm -rf survey_summaries_html

# 再生成
./generate_summaries.sh
```

または特定のトピックのみ：

```bash
python generate_survey_summaries.py --topics marumie-shikin-user
```

## 💡 ヒント

### より良い要約を得るために

1. **十分なデータ**: 各トピック30件以上の回答が理想的
2. **高品質な回答**: 品質フィルタリング（`ingest_data.py`）が重要
3. **適切なモデル**: より大きいモデルほど詳細な分析が可能
4. **コンテキスト**: `--max-docs` を増やすとより包括的な分析

### パフォーマンス最適化

1. **並列処理**: 複数のトピックを同時に処理したい場合は手動で実行
2. **バッチ処理**: 夜間など時間のある時に一括実行
3. **キャッシュ**: 同じトピックの再処理を避ける

### カスタマイズ

スクリプトをカスタマイズする場合：
- `generate_survey_summaries.py` の `template` を編集して要約の形式を変更
- HTMLスタイルを `generate_html_report()` 内で調整
- 統計情報の表示を `analyze_topic_data()` でカスタマイズ

## 📚 関連ファイル

- `generate_survey_summaries.py`: メインスクリプト
- `generate_summaries.sh`: 実行ヘルパースクリプト
- `ingest_data.py`: データ準備用
- `app.py`: インタラクティブな質問応答UI

## 🎉 完成イメージ

生成されるHTMLは以下の特徴を持ちます：

- 📊 **プロフェッショナルな見た目**: グラデーション、カード、表
- 📱 **モバイル対応**: どのデバイスでも見やすい
- 🖨️ **印刷可能**: レポートとして印刷可能
- 📈 **データドリブン**: 実際のデータに基づく詳細な分析
- 🎨 **視覚的**: 色分け、アイコン、レイアウト

---

**作成日**: 2025-11-23  
**Python環境**: mirai_db_analysis_py3.11










