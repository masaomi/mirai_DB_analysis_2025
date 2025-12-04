# Survey Report Viewer

アンケート分析レポートを表示し、LLMを使ったQ&A機能を提供するNext.jsアプリケーションです。

## 機能

- **レポート一覧**: 利用可能なレポートをカード形式で表示
- **レポート詳細**: Markdown形式のレポートをHTML表示
- **チャート表示**: 分析パイプラインで生成されたチャートを表示
- **Q&A Chat**: レポートについてLLMに質問できるチャット機能
  - **シンプルモード**: レポートと分析データをコンテキストとして使用
  - **RAGモード**: ChromaDBでセマンティック検索して関連回答を取得

## システム構成

```
┌─────────────────────────────────────────────────────────────┐
│                    Next.js Application                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ レポート一覧 │  │ レポート詳細 │  │    Q&A Chat        │  │
│  │   /         │  │ /reports/   │  │    /qa/[slug]      │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│                                              │               │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                    API Routes                           ││
│  │  /api/reports  /api/charts  /api/qa                    ││
│  └─────────────────────────────────────────────────────────┘│
└────────────────────────────┬────────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ RAG Server      │ │ LLM Provider    │ │ Static Files    │
│ (port 8001)     │ │ Bedrock/Ollama  │ │ outputs/        │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

## 前提条件

- Node.js 18以上
- pnpm (推奨) または npm
- `survey_analysis_pipeline/` でレポートが生成されていること
- RAGモード使用時: RAGサーバーが起動していること

## インストール

```bash
cd survey_report_viewer

# 依存関係インストール
pnpm install
# または
npm install

# 環境変数を設定
cp .env.example .env
# .envファイルを編集してLLMプロバイダーを設定
```

## 使用方法

### 開発サーバー起動

```bash
pnpm dev
# または
npm run dev
```

ブラウザで http://localhost:3000 を開く

### プロダクションビルド

```bash
pnpm build
pnpm start

# ポート指定
PORT=3002 pnpm start
```

### Q&A機能の使用

#### シンプルモード（デフォルト）

レポートと分析データをLLMのコンテキストとして使用します。
RAGサーバー不要で動作します。

```
http://localhost:3000/qa/bill-of-lading
http://localhost:3000/qa/bill-of-lading?mode=simple
```

#### RAGモード

ChromaDBでセマンティック検索を行い、関連する個別回答を取得します。
RAGサーバーの起動が必要です。

```bash
# 1. RAGサーバー起動 (survey_analysis_pipeline/)
cd ../survey_analysis_pipeline
pixi run python rag_server.py bill-of-lading --port 8001

# 2. Next.jsサーバー起動
cd ../survey_report_viewer
pnpm start
```

```
http://localhost:3000/qa/bill-of-lading?mode=rag
```

## 環境変数

### LLMプロバイダー設定

#### Ollama (ローカル)

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

#### Amazon Bedrock

```env
LLM_PROVIDER=bedrock
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
```

#### OpenRouter

```env
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=your_api_key
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet
```

### RAGサーバー設定

```env
RAG_SERVER_URL=http://localhost:8001
```

## API エンドポイント

| エンドポイント | メソッド | 説明 |
|--------------|---------|------|
| `/api/reports` | GET | レポート一覧取得 |
| `/api/reports/[slug]` | GET | レポート詳細取得 |
| `/api/charts/[slug]/[filename]` | GET | チャート画像取得 |
| `/api/qa` | POST | Q&A (LLMストリーミング) |

### Q&A API パラメータ

| パラメータ | 説明 | デフォルト |
|-----------|------|-----------|
| `slug` | アンケートスラッグ (URLパラメータ) | 必須 |
| `mode` | `simple` または `rag` | `simple` |

**リクエスト例:**

```bash
curl -X POST "http://localhost:3000/api/qa?slug=bill-of-lading&mode=rag" \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "賛成派の主な理由は？"}], "slug": "bill-of-lading"}'
```

## ディレクトリ構成

```
survey_report_viewer/
├── app/
│   ├── api/
│   │   ├── charts/[slug]/[filename]/route.ts  # チャート配信
│   │   ├── qa/route.ts                        # Q&A API (LLM + RAG)
│   │   └── reports/                           # レポートAPI
│   │       ├── route.ts                       # 一覧取得
│   │       └── [slug]/route.ts                # 詳細取得
│   ├── reports/[slug]/page.tsx                # レポート詳細ページ
│   ├── qa/[slug]/page.tsx                     # Q&Aチャットページ
│   ├── globals.css                            # グローバルスタイル
│   ├── layout.tsx                             # レイアウト
│   └── page.tsx                               # ホームページ（一覧）
├── .env.example                               # 環境変数サンプル
├── package.json
├── tailwind.config.ts
├── tsconfig.json
└── next.config.ts
```

## データ連携

このアプリは `survey_analysis_pipeline/` で生成されたレポートを読み込みます。

```
survey_analysis_pipeline/outputs/{survey_slug}/
├── report.md              # Markdownレポート → レポート表示
├── analysis_data.json     # 分析データ → メタ情報・Q&Aコンテキスト
├── charts/                # チャート画像 → チャート表示
└── vector_index/          # RAGインデックス → RAGモードで使用
```

## 実装状況

| 機能 | 状態 |
|------|------|
| レポート一覧表示 | ✅ 実装済み |
| レポート詳細表示 | ✅ 実装済み |
| チャート表示 | ✅ 実装済み |
| Q&A チャットUI | ✅ 実装済み |
| Q&A API (シンプルモード) | ✅ 実装済み |
| Q&A API (RAGモード) | ✅ 実装済み |
| ストリーミング回答 | ✅ 実装済み |
| モード切替UI | ✅ 実装済み |

## 技術スタック

| コンポーネント | 技術 |
|--------------|------|
| フレームワーク | Next.js 15 (App Router) |
| スタイリング | Tailwind CSS |
| LLM統合 | Vercel AI SDK |
| LLMプロバイダー | Ollama, Amazon Bedrock, OpenRouter |
| Markdown | react-markdown, remark-gfm |
| アイコン | Lucide React |

## クイックスタート

```bash
# 1. survey_analysis_pipeline でレポート生成
cd survey_analysis_pipeline
pixi run python main.py analyze bill-of-lading

# 2. RAGサーバー起動 (RAGモード使用時)
pixi run python rag_server.py bill-of-lading --port 8001

# 3. Next.js起動
cd ../survey_report_viewer
pnpm install
pnpm build
pnpm start

# 4. ブラウザでアクセス
# レポート: http://localhost:3000/reports/bill-of-lading
# Q&A (RAG): http://localhost:3000/qa/bill-of-lading?mode=rag
```

## ライセンス

MIT
