# Gemini 3 Pro Preview を使ったアンケート要約

このドキュメントでは、Google API経由でGemini 3 Pro Previewを使ってアンケート回答を要約する方法を説明します。

## 必要な環境

- Python 3.11以上
- Conda環境: `mirai_db_analysis_py3.11`
- Google AI API Key

## セットアップ手順

### 1. Conda環境のアクティベート

```bash
conda activate mirai_db_analysis_py3.11
```

### 2. 必要なパッケージのインストール

```bash
cd survey_analysis
pip install -r requirements.txt
```

### 3. API Keyの設定

`.env`ファイルを作成してGoogle API Keyを設定します：

```bash
# サンプルファイルをコピー
cp env_sample.txt .env

# エディタで.envファイルを編集
nano .env
```

`.env`ファイルの内容（`env_sample.txt`に詳細なコメント付き）：

```
GOOGLE_API_KEY=あなたのAPIキー
```

#### Google API Keyの取得方法

1. [Google AI Studio](https://aistudio.google.com/app/apikey) にアクセス
2. 「Create API Key」をクリック
3. 生成されたAPIキーをコピー
4. `.env`ファイルに貼り付け

## 使用方法

### 基本的な使い方

```bash
# デフォルトモデル（gemini-exp-1206）で実行
python summarize_surveys_gemini3.py
```

### 利用可能なモデル

以下の3つのGemini 3 Pro Previewモデルが利用可能です：

1. **exp-1206** (デフォルト)
   - モデル名: `gemini-exp-1206`
   - Gemini 3 Pro Preview（2024年12月版）
   - 推奨モデル

2. **2.0-flash-exp**
   - モデル名: `gemini-2.0-flash-exp`
   - Gemini 2.0 Flash Experimental
   - 高速処理向け

3. **2.0-flash-thinking-exp**
   - モデル名: `gemini-2.0-flash-thinking-exp-1219`
   - 思考プロセス付きモデル
   - より詳細な分析に適している

### オプション付きの実行例

```bash
# 特定のモデルを指定
python summarize_surveys_gemini3.py --model 2.0-flash-exp

# 特定のアンケートのみ処理
python summarize_surveys_gemini3.py --survey plan2026

# バッチサイズを変更（大きくすると処理が速いが、APIリクエストが大きくなる）
python summarize_surveys_gemini3.py --batch-size 20

# 複数オプションの組み合わせ
python summarize_surveys_gemini3.py --model exp-1206 --survey plan2026 --batch-size 15
```

### ヘルプの表示

```bash
python summarize_surveys_gemini3.py --help
```

## 出力結果

処理結果は以下のディレクトリに保存されます：

```
survey_summaries/
└── gemini3/
    └── summaries/
        ├── survey1_summary.json
        ├── survey2_summary.json
        └── ...
```

### 出力フォーマット

各サマリーファイルには以下の情報が含まれます：

```json
{
  "slug": "アンケートのスラッグ",
  "title": "アンケートのタイトル",
  "description": "アンケートの説明",
  "num_sessions": 100,
  "num_questions": 5,
  "provider": "gemini3",
  "model": "gemini-exp-1206",
  "question_summaries": [
    {
      "question_id": "q1",
      "question": "質問テキスト",
      "topic": "トピック",
      "num_responses": 50,
      "summary": "要約テキスト"
    }
  ]
}
```

## 処理の流れ

1. **データ読み込み**: `survey_chunks/`から調査データを読み込む
2. **QA抽出**: 質問と回答のペアを抽出
3. **バッチ処理**: 回答数が多い場合、適切なバッチサイズに分割
4. **要約生成**: Gemini 3 Pro Previewで各質問の回答を要約
5. **階層的統合**: バッチが多い場合、階層的に統合
6. **結果保存**: JSON形式で保存

## トラブルシューティング

### API Keyエラー

```
❌ Error: GOOGLE_API_KEY not found in environment variables
```

**解決方法**: `.env`ファイルが正しく作成されているか確認してください。

### レート制限エラー

```
⚠️ Rate limit hit, waiting 2s...
```

**説明**: APIのレート制限に達した場合、自動的に待機して再試行します。

### モジュールが見つからないエラー

```
ModuleNotFoundError: No module named 'google.generativeai'
```

**解決方法**: 
```bash
conda activate mirai_db_analysis_py3.11
pip install -r requirements.txt
```

## パフォーマンスの最適化

### バッチサイズの調整

- **小さいバッチサイズ (5-10)**: より詳細な分析、処理時間が長い
- **中程度のバッチサイズ (10-20)**: バランスが良い（推奨）
- **大きいバッチサイズ (20-50)**: 高速処理、詳細度が若干低下

### モデルの選択

- **exp-1206**: 最もバランスが良い、推奨
- **2.0-flash-exp**: 処理速度重視
- **2.0-flash-thinking-exp**: 分析の質重視

## 注意事項

1. **API使用量**: Google AI APIの無料枠や使用制限に注意してください
2. **処理時間**: アンケートの規模によって処理時間が大きく変わります
3. **エラー処理**: ネットワークエラーやAPIエラーは自動的にリトライされます（最大3回）

## サポート

問題が発生した場合は、以下を確認してください：

1. Conda環境が正しくアクティベートされているか
2. `.env`ファイルが正しく設定されているか
3. インターネット接続が安定しているか
4. Google AI APIのステータスを確認

## 関連ドキュメント

- [Google AI for Developers](https://ai.google.dev/)
- [Gemini API Documentation](https://ai.google.dev/docs)
- [元のスクリプト](./summarize_surveys.py)

