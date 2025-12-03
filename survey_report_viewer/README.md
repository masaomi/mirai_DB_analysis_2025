# Survey Report Viewer

アンケート分析レポートを表示し、LLMを使ったQ&A機能を提供するNext.jsアプリケーションです。

## 機能

- **レポート表示**: Markdown形式のレポートをHTML表示
- **チャート表示**: 分析パイプラインで生成されたチャートを表示
- **Q&A Chat**: レポートについてLLMに質問できるRAG + Chat機能 (実装予定)

## 前提条件

- Node.js 18以上
- pnpm (推奨) または npm
- `survey_analysis_pipeline/` でレポートが生成されていること

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
```

## ディレクトリ構成

```
survey_report_viewer/
├── app/
│   ├── api/
│   │   ├── charts/[slug]/[filename]/route.ts  # チャート配信API
│   │   ├── qa/route.ts                        # Q&A API (LLM統合予定)
│   │   └── reports/                           # レポート取得API
│   │       ├── route.ts                       # 一覧取得
│   │       └── [slug]/route.ts                # 詳細取得
│   ├── reports/[slug]/page.tsx                # レポート詳細ページ
│   ├── qa/[slug]/page.tsx                     # Q&Aチャットページ (未実装)
│   ├── globals.css                            # グローバルスタイル
│   ├── layout.tsx                             # レイアウト
│   └── page.tsx                               # ホームページ（レポート一覧）
├── package.json
├── tailwind.config.ts
├── tsconfig.json
└── next.config.ts
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

## データ連携

このアプリは `survey_analysis_pipeline/` で生成されたレポートを読み込みます。

```
survey_analysis_pipeline/outputs/{survey_slug}/
├── report.md              # Markdownレポート → レポート表示
├── analysis_data.json     # 分析データ → メタ情報表示
├── charts/                # チャート画像 → チャート表示
└── vector_index/          # RAGインデックス → Q&A機能
```

## 実装状況

| 機能 | 状態 |
|------|------|
| レポート一覧表示 | ✅ 実装済み |
| レポート詳細表示 | ✅ 実装済み |
| チャート表示 | ✅ 実装済み |
| Q&A API | ⚠️ プレースホルダー（LLM呼び出し未実装） |
| Q&A チャットUI | ❌ 未実装 |
| RAG検索 | ⚠️ キーワードマッチのみ（ベクトル検索未実装） |

## 今後の実装予定

1. **Q&Aページの実装** (`/qa/[slug]/page.tsx`)
   - チャットUI
   - ストリーミング回答表示

2. **Q&A APIのLLM統合** (`/api/qa/route.ts`)
   - Ollama / Bedrock / OpenRouter 対応
   - RAG（ChromaDB）との統合
   - ストリーミングレスポンス

3. **インタラクティブチャート**
   - Recharts / Plotlyでのインタラクティブ表示

## ライセンス

MIT

