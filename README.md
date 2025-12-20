# Survey Analysis System

AI駆動のアンケート分析システム - 自由記述式アンケートデータを自動解析し、レポート生成・Q&A機能を提供する統合システムです。

## システムの特徴

- **AIと機械的手法の合成**による（ほぼ）全自動レポート生成
- **インタラクティブ**による深掘りQ&A
- **専門家AI**とのディスカッション（ペルソナアセンブリ）

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
│  │  • 論点ファイル読込        │      │  • レポート表示           │         │
│  │  • クラスタリング          │      │  • Q&A Chat (RAG)        │         │
│  │  • 立場検出                │ ───→ │  • ペルソナ Assembly      │         │
│  │  • Multi-LLM 合意形成      │      │                          │         │
│  │  • レポート生成            │      │                          │         │
│  │  • RAGインデックス         │      │                          │         │
│  └──────────────────────────┘      └──────────────────────────┘         │
│           │                                   │                          │
│           ▼                                   ▼                          │
│  ┌──────────────────────────────────────────────────────────────┐       │
│  │  outputs/{slug}/                                              │       │
│  │  ├── report.md          # Markdownレポート                    │       │
│  │  ├── analysis_data.json # 分析データ                          │       │
│  │  ├── multi_llm/         # Multi-LLM議論ログ                   │       │
│  │  └── vector_index/      # RAGインデックス                     │       │
│  └──────────────────────────────────────────────────────────────┘       │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## 主要機能

### 分析パイプライン (survey_analysis_pipeline)

| 機能 | 説明 |
|-----|------|
| **Multi-LLM Orchestration** | 複数LLM（Claude, GPT, Gemini等）による合意形成 → **エグゼクティブサマリー**生成 |
| **論点ベース分析** | 法制審議会の論点（`*_ronten.txt`）に沿った意見集約 |
| **意見クラスタリング** | HDBSCAN + Embeddingで類似意見をグループ化 |
| **立場検出** | 賛成/反対/中立を自動判定 |
| **マイノリティ検出** | 少数派だが重要な意見を抽出 |
| **レポート生成** | Markdown/HTML形式のレポート自動生成 |

### Webビューア (survey_report_viewer)

| 機能 | 説明 |
|-----|------|
| **レポート表示** | 生成されたレポートをWeb UIで閲覧 |
| **Q&A Chat** | レポートについてLLMに質問（シンプル/RAGモード） |
| **ペルソナアセンブリ** | 生成されたレポートの深掘り・検証ツール |

### ペルソナアセンブリ

レポートをもとに見落としがないか、さらに深掘りするためのツールです。

| ペルソナ | 主な観点 |
|:--------|:--------|
| **政策立案者** | 実装可能性、予算、ロードマップ |
| **批判的研究者** | リスク、見落とし、長期影響 |
| **技術専門家** | 技術的実現性、インフラ、セキュリティ |
| **経済専門家** | 費用対効果、経済波及効果、持続可能性 |

- リアルタイムSSE配信で議論をストリーミング表示
- ユーザーが議論に割り込んで質問・指摘が可能

## 分析済みレポート

| 法案 | 回答数 | 主な知見 |
|-----|-------|---------|
| **船荷証券電子化法案** | 2,148件 | セキュリティ対策、国際標準適合、中小企業支援が成功要因 |
| **国会議員定数削減法案** | 11,359件 | 「ゾンビ議員」への不満が広く共有、選挙制度全体の見直しが必要 |
| **人工知能基本計画法案** | 11,566件 | 認知度の低さが課題、医療・防災・行政がAI導入の最優先分野 |

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
cp env-sample.txt .env
# .envを編集してLLMプロバイダーを設定
```

### 2. アンケート分析

```bash
cd survey_analysis_pipeline

# 利用可能なアンケート一覧
pixi run python main.py list-surveys

# 分析実行（Multi-LLM + ペルソナ有効）
pixi run python main.py analyze bill-of-lading --multi-llm --persona
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
- **Q&A (RAG)**: http://localhost:3000/qa/bill-of-lading?mode=rag
- **ペルソナ Assembly**: http://localhost:3000/persona?slug=bill-of-lading

## 論点ベース分析 (Ronten)

法制審議会の論点をあらかじめ `{survey_slug}_ronten.txt` として定義し、意見を論点にマッチングさせます。

```
survey_analysis_pipeline/
├── pipeline/extractors/ronten_loader.py   # 論点ファイル読込
└── pipeline/analyzers/ronten_matcher.py   # 意見を論点にマッチング
```

### 船荷証券の論点例
- 機能的同等性（MLETR準拠）
- 「支配」概念の具体化
- 情報システム提供者の法的地位
- 強制執行の実効性確保
- 紙と電子の相互転換

## Multi-LLM Orchestration

複数のLLMが並列で分析し、相互評価・合意形成を行います。

```
orchestration/multi_llm.py
```

- **複数LLM並列分析**: Claude Opus, Sonnet, GPT, Gemini など
- **相互評価**: 0-10点で品質スコアリング
- **反復ディスカッション**: 合意閾値(80%)に達するまで議論
- **差異の明確化**: 合意点・対立点を抽出

### 出力成果物

```
outputs/{slug}/multi_llm/
├── consensus_report.md      # 統合レポート（エグゼクティブサマリー）
├── discussion_log.md        # 議論ログ
├── evaluation_matrix.json   # 評価マトリクス
└── {model}_output.md        # 各モデルの個別出力
```

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
mirai_DB_analysis_2025/
├── survey_analysis_pipeline/   # Python分析パイプライン
│   ├── main.py                # CLIエントリーポイント
│   ├── rag_server.py          # RAG検索サーバー
│   ├── config/                # 設定ファイル
│   ├── core/                  # コアモジュール (LLMクライアント)
│   ├── pipeline/              # パイプラインモジュール
│   │   ├── extractors/       # データ抽出 (ronten_loader含む)
│   │   ├── analyzers/        # 分析 (ronten_matcher含む)
│   │   ├── summarizers/      # 要約
│   │   └── generators/       # 出力生成
│   ├── orchestration/         # Multi LLM / Persona Assembly
│   └── outputs/               # 生成されたレポート
│
├── survey_report_viewer/       # Next.js Webビューア
│   ├── app/                   # App Router
│   │   ├── api/              # API Routes
│   │   ├── reports/          # レポートページ
│   │   ├── qa/               # Q&Aページ
│   │   ├── persona/          # ペルソナAssemblyページ
│   │   └── components/       # UIコンポーネント
│   └── package.json
│
├── data/                       # アンケートCSVデータ
│   └── *_ronten.txt           # 論点定義ファイル
│
└── README.md                  # このファイル
```

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
| ストリーミング | SSE (Server-Sent Events) |
| Markdown | react-markdown, remark-gfm |

## 詳細ドキュメント

- [survey_analysis_pipeline/README.md](survey_analysis_pipeline/README.md) - Python分析パイプラインの詳細
- [survey_report_viewer/README.md](survey_report_viewer/README.md) - Next.js Webビューアの詳細

## ライセンス

MIT

## Author

Masa@Swiss
