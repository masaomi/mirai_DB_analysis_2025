# Survey Analysis Pipeline

アンケート調査データを分析し、レポートを自動生成するPython CLIアプリケーションです。

## 機能

- **データ抽出**: CSVファイルからアンケート回答を抽出
- **立場検出**: 賛成/反対/中立の立場を自動判定
- **クラスタリング**: 類似意見をグループ化
- **マイノリティ検出**: 少数派だが重要な意見を検出
- **LLM要約**: Map-Reduce方式による階層的要約
- **Multi LLM Orchestration**: 複数LLMによる合意形成 (オプション)
- **Persona Assembly**: 多視点分析 (オプション)
- **レポート生成**: Markdown/HTML形式のレポート
- **チャート生成**: 立場分布、クラスタサイズ、ワードクラウド
- **RAGインデックス**: レポートQ&A用のベクトルインデックス

## インストール

### 前提条件

- [pixi](https://pixi.sh/) がインストールされていること

### セットアップ

```bash
cd survey_analysis_pipeline

# pixi環境をセットアップ
pixi install

# 環境変数を設定
cp env_example.txt .env
# .envファイルを編集してLLMプロバイダーを設定
```

## 使用方法

### 利用可能なアンケート一覧

```bash
pixi run python main.py list-surveys
```

### 単一アンケートの分析

```bash
# 基本分析
pixi run python main.py analyze ai-plan-test

# Multi LLM Orchestrationを有効化
pixi run python main.py analyze ai-plan-test --multi-llm

# Persona Assemblyを有効化
pixi run python main.py analyze ai-plan-test --persona

# 両方を有効化
pixi run python main.py analyze ai-plan-test --multi-llm --persona

# LLMプロバイダーを指定
pixi run python main.py analyze ai-plan-test --provider bedrock

# 出力ディレクトリを指定
pixi run python main.py analyze ai-plan-test --output ./my_output
```

### バッチ処理

```bash
# 設定ファイルを編集
vim config/batch_jobs.yaml

# バッチ実行
pixi run python main.py batch config/batch_jobs.yaml
```

### RAGクエリ

```bash
pixi run python main.py query ai-plan-test "主な賛成意見は何ですか？"
```

## LLMプロバイダー設定

### Ollama (ローカル)

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

### Amazon Bedrock

```env
LLM_PROVIDER=bedrock
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
```

### OpenRouter

```env
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=your_api_key
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet
```

## 出力構成

```
outputs/{survey_slug}/
├── report.md              # Markdownレポート
├── report.html            # HTMLレポート
├── analysis_data.json     # 分析データ (JSON)
├── charts/
│   ├── stance_distribution.png  # 立場分布
│   ├── cluster_sizes.png        # クラスタサイズ
│   └── wordcloud.png            # ワードクラウド
└── vector_index/          # RAGインデックス
    ├── chroma.sqlite3
    └── metadata.json
```

## CLIオプション

### `analyze` コマンド

| オプション | 短縮形 | 説明 |
|-----------|-------|------|
| `--output` | `-o` | 出力ディレクトリ |
| `--provider` | `-p` | LLMプロバイダー (ollama, bedrock, openrouter) |
| `--multi-llm` | `-m` | Multi LLM Orchestrationを有効化 |
| `--persona` | `-P` | Persona Assemblyを有効化 |
| `--skip-summarization` | | LLM要約をスキップ |
| `--skip-charts` | | チャート生成をスキップ |
| `--skip-index` | | RAGインデックス生成をスキップ |

## ディレクトリ構成

```
survey_analysis_pipeline/
├── config/                 # 設定ファイル
│   ├── settings.py        # Pydantic設定
│   ├── batch_jobs.yaml    # バッチ処理設定
│   └── prompts/           # プロンプトテンプレート
├── core/                   # コアモジュール
│   └── llm_client.py      # LLMクライアント
├── pipeline/               # パイプラインモジュール
│   ├── extractors/        # データ抽出
│   ├── analyzers/         # 分析
│   ├── summarizers/       # 要約
│   └── generators/        # 出力生成
├── orchestration/          # オーケストレーション
│   ├── multi_llm.py       # Multi LLM
│   └── persona_assembly.py # Persona Assembly
├── main.py                 # CLIエントリーポイント
└── pixi.toml              # 依存関係定義
```

## ライセンス

MIT

