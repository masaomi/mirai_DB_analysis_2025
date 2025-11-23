# Survey RAG App - クイックスタートガイド

## 🎯 環境: mirai_db_analysis_py3.11

このアプリは `mirai_db_analysis_py3.11` conda環境で動作するようにセットアップ済みです。

## 📦 セットアップ完了

✅ Python 3.11.14  
✅ すべての依存パッケージがインストール済み  
✅ 起動スクリプトが作成済み

## 🚀 使い方

### 1. データのIngestion（初回のみ）

```bash
cd /Users/masa/forback/github/mirai_DB_backup/survey_rag_app
./ingest.sh
```

または手動で：

```bash
conda activate mirai_db_analysis_py3.11
cd /Users/masa/forback/github/mirai_DB_backup/survey_rag_app
python ingest_data.py
```

**処理内容:**
- 約65,000件のアンケート回答を読み込み
- 品質フィルタリング（5文字以上、意味のある回答のみ）
- 感情分析（-1.0〜+1.0のスコア）
- 重複検出（完全一致と類似回答）
- ベクターDB（ChromaDB）の作成
- 統計情報のJSON出力

**所要時間:** 2-5分程度

### 2. アプリの起動

```bash
cd /Users/masa/forback/github/mirai_DB_backup/survey_rag_app
./start_app.sh
```

または手動で：

```bash
conda activate mirai_db_analysis_py3.11
cd /Users/masa/forback/github/mirai_DB_backup/survey_rag_app
streamlit run app.py
```

**アクセス:**  
ブラウザで http://localhost:8501 を開く

### 3. サーバーの停止

ターミナルで `Ctrl + C` を押す

## 🔧 設定

アプリ起動後、サイドバーでLLMプロバイダーを選択：

### オプション1: Ollama（ローカル）

```bash
# 別のターミナルで
ollama serve

# モデルのpull（初回のみ）
ollama pull gpt-oss:20b
```

アプリ設定：
- Base URL: `http://localhost:11434`
- Model Name: `gpt-oss:20b`

### オプション2: AWS Bedrock（クラウド）

```bash
# AWS認証情報の設定
aws configure
```

アプリ設定：
- AWS Region: `us-east-1`
- Model ID: `anthropic.claude-3-5-sonnet-20240620-v1:0`
- AWS Profile: 設定したprofile名

## 📊 機能

### 基本機能
- アンケート回答の検索と要約
- 65,000+件のデータから関連回答を抽出
- AIによる集約回答の生成

### フィルター機能
- トピック別検索
- 日付範囲指定
- 品質レベル選択（high/medium/low）
- 感情分析フィルター（positive/neutral/negative等）
- キーワードフィルター（ポジティブ/ネガティブ/政策関連）
- 重複除外機能

### 統計表示
- 参照回答数
- トピック分布
- 品質分布
- 感情スコア
- キーワード統計

## 📁 ファイル構成

```
survey_rag_app/
├── ingest.sh              # データingestion用スクリプト
├── start_app.sh           # アプリ起動用スクリプト
├── ingest_data.py         # Ingestion処理本体
├── app.py                 # Streamlitアプリ本体
├── requirements.txt       # Pythonパッケージリスト
├── README.md              # 詳細ドキュメント
├── ENHANCED_FEATURES.md   # 機能詳細
├── QUICKSTART.md          # このファイル
├── chroma_db/             # ベクターDB（ingestion後）
└── ingestion_statistics.json  # 統計情報（ingestion後）
```

## 🐛 トラブルシューティング

### "ChromaDB not found"

```bash
./ingest.sh
```

を実行してDBを作成してください。

### ポートが使用中

```bash
streamlit run app.py --server.port 8502
```

で別のポートを使用してください。

### Conda環境が見つからない

```bash
conda env list
```

で `mirai_db_analysis_py3.11` が存在することを確認してください。

## 📚 詳細ドキュメント

- **README.md**: 完全なドキュメント
- **ENHANCED_FEATURES.md**: 新機能の詳細説明

## 🎉 サンプル質問

アプリで試せる質問例：

1. "国会議員定数削減についてどう思いますか？"
2. "人工知能についての期待は？"
3. "政策に関するポジティブな意見を教えてください"
4. "2025年上半期の回答傾向は？"

フィルターと組み合わせることで、より詳細な分析が可能です！

---

**セットアップ完了日**: 2025-11-23  
**Python環境**: mirai_db_analysis_py3.11 (Python 3.11.14)

