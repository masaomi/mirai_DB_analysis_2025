# Survey Analysis System

自由記述式アンケートデータを自動解析し、レポート生成・Q&A機能を提供する統合システムです。

## システム概要

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Survey Analysis System                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────────────┐      ┌──────────────────────────┐         │
│  │  survey_analysis_pipeline │      │  survey_report_viewer    │         │
│  │  (Python CLI)             │      │  (Next.js Web App)       │         │
│  │                           │      │                          │         │
│  │  • データ抽出              │      │  • レポート表示           │         │
│  │  • 立場検出                │      │  • チャート表示           │         │
│  │  • クラスタリング          │ ───→ │  • Q&A Chat              │         │
│  │  • LLM要約                │      │  • RAGモード対応          │         │
│  │  • レポート生成            │      │                          │         │
│  │  • RAGインデックス         │      │                          │         │
│  │  • RAGサーバー             │      │                          │         │
│  └──────────────────────────┘      └──────────────────────────┘         │
│           │                                   │                          │
│           ▼                                   ▼                          │
│  ┌──────────────────────────────────────────────────────────────┐       │
│  │  outputs/{slug}/                                              │       │
│  │  ├── report.md          # Markdownレポート                    │       │
│  │  ├── analysis_data.json # 分析データ                          │       │
│  │  ├── charts/            # チャート画像                        │       │
│  │  └── vector_index/      # RAGインデックス                     │       │
│  └──────────────────────────────────────────────────────────────┘       │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## 主要機能

| 機能 | 説明 |
|-----|------|
| **自動立場検出** | 賛成/反対/中立を自動判定 |
| **意見クラスタリング** | 類似意見をHDBSCANでグループ化 |
| **マイノリティ検出** | 少数派だが重要な意見を抽出 |
| **LLM要約** | Map-Reduce方式による階層的要約 |
| **Multi LLM** | 複数LLMによる合意形成（オプション） |
| **Persona Assembly** | 多視点分析（オプション） |
| **チャート生成** | 立場分布、クラスタサイズ、ワードクラウド |
| **Q&A Chat** | レポートについてLLMに質問 |
| **RAG検索** | セマンティック検索で関連回答を取得 |

## クイックスタート

### 1. セットアップ

```bash
# Python環境（pixi）
cd survey_analysis_pipeline
pixi install
cp env_example.txt .env
# .envを編集してLLMプロバイダーを設定

# Next.js環境
cd ../survey_report_viewer
pnpm install
cp .env.example .env
# .envを編集してLLMプロバイダーを設定
```

### 2. アンケート分析

```bash
cd survey_analysis_pipeline

# 利用可能なアンケート一覧
pixi run python main.py list-surveys

# 分析実行
pixi run python main.py analyze bill-of-lading
```

### 3. RAGサーバー起動（Q&A用）

```bash
cd survey_analysis_pipeline
pixi run python rag_server.py bill-of-lading --port 8001
```

### 4. Webビューア起動

```bash
cd survey_report_viewer
pnpm build && pnpm start
```

### 5. ブラウザでアクセス

- **レポート一覧**: http://localhost:3000
- **レポート詳細**: http://localhost:3000/reports/bill-of-lading
- **Q&A (シンプル)**: http://localhost:3000/qa/bill-of-lading?mode=simple
- **Q&A (RAG)**: http://localhost:3000/qa/bill-of-lading?mode=rag

## データセット

### データ概要

| 項目 | 内容 |
|------|------|
| バックアップファイル | `backup-2025-11-14T03-19-14.json` / `.sql` |
| データ種別 | PostgreSQL形式のデータベースバックアップ |
| セッション数 | 15,341件 |
| メッセージ数 | 142,237件（ユーザー回答65,318件） |

### 主要トピック

| トピック | セッション数 |
|---------|------------|
| 国会議員定数削減 | 6,604 |
| 人工知能基本計画 | 4,561 |
| チームみらい1年プラン | 2,403 |
| 船荷証券の電子化法案 | 888 |

## LLMプロバイダー

3つのLLMプロバイダーに対応しています：

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

## ディレクトリ構成

```
mirai_DB_backup/
├── survey_analysis_pipeline/   # Python分析パイプライン
│   ├── main.py                # CLIエントリーポイント
│   ├── rag_server.py          # RAG検索サーバー
│   ├── config/                # 設定ファイル
│   ├── core/                  # コアモジュール
│   ├── pipeline/              # パイプラインモジュール
│   ├── orchestration/         # Multi LLM / Persona
│   └── outputs/               # 生成されたレポート
│
├── survey_report_viewer/       # Next.js Webビューア
│   ├── app/                   # App Router
│   │   ├── api/              # API Routes
│   │   ├── reports/          # レポートページ
│   │   └── qa/               # Q&Aページ
│   └── package.json
│
├── data/                       # アンケートCSVデータ
│   ├── bill-of-lading_messages.csv
│   └── ...
│
├── backup-*.json              # 元データバックアップ
└── README.md                  # このファイル
```

## 詳細ドキュメント

- [survey_analysis_pipeline/README.md](survey_analysis_pipeline/README.md) - Python分析パイプラインの詳細
- [survey_report_viewer/README.md](survey_report_viewer/README.md) - Next.js Webビューアの詳細
- [README_old.md](README_old.md) - 旧版の解析ツール（参考用）

## 技術スタック

### Python Pipeline

| コンポーネント | 技術 |
|--------------|------|
| 環境管理 | pixi, Python 3.12 |
| LLM統合 | litellm |
| CLI | typer, rich |
| 分析 | pandas, scikit-learn, hdbscan, umap-learn |
| 埋め込み | sentence-transformers (multilingual-e5-base) |
| ベクトルDB | ChromaDB |
| 可視化 | matplotlib, plotly, wordcloud |
| APIサーバー | FastAPI, uvicorn |

### Next.js Viewer

| コンポーネント | 技術 |
|--------------|------|
| フレームワーク | Next.js 15 (App Router) |
| スタイリング | Tailwind CSS |
| LLM統合 | Vercel AI SDK |
| Markdown | react-markdown, remark-gfm |

## ライセンス

MIT
