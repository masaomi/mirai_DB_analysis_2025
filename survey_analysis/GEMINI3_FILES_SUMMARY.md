# Gemini 3 Pro Preview 関連ファイル一覧

## 📁 作成されたファイル

### 1. メインスクリプト

#### `summarize_surveys_gemini3.py` ⭐
**用途**: アンケート回答をGemini 3 Pro Previewで要約するメインスクリプト

**特徴**:
- Google API経由でGemini 3 Pro Previewを使用
- `.env`ファイルからAPI Keyを読み込み
- 3つのGemini 3モデルをサポート:
  - `gemini-exp-1206` (デフォルト、推奨)
  - `gemini-2.0-flash-exp` (高速)
  - `gemini-2.0-flash-thinking-exp-1219` (詳細分析)
- バッチ処理と階層的要約をサポート
- 自動リトライ機能（レート制限対応）

**実行例**:
```bash
python summarize_surveys_gemini3.py
python summarize_surveys_gemini3.py --model 2.0-flash-exp --batch-size 20
python summarize_surveys_gemini3.py --survey plan2026
```

---

### 2. セットアップ関連

#### `setup_gemini3.sh`
**用途**: 初回セットアップを自動化するシェルスクリプト

**機能**:
- パッケージの自動インストール
- `.env`ファイルの自動作成
- 出力ディレクトリの作成
- 環境チェック

**実行方法**:
```bash
chmod +x setup_gemini3.sh  # 初回のみ
./setup_gemini3.sh
```

---

#### `test_gemini3_connection.py`
**用途**: API接続をテストするスクリプト

**機能**:
- API Key設定の確認
- Gemini API接続テスト
- 環境チェック（Python、パッケージ、Conda環境）
- サンプルプロンプトでの動作確認

**実行方法**:
```bash
python test_gemini3_connection.py
python test_gemini3_connection.py --model 2.0-flash-exp
```

---

### 3. ドキュメント

#### `README_GEMINI3.md`
**用途**: 詳細なドキュメント

**内容**:
- セットアップ手順の詳細
- 全オプションの説明
- トラブルシューティング
- パフォーマンス最適化のTips

---

#### `QUICKSTART_GEMINI3.md`
**用途**: 5分で始められるクイックスタートガイド

**内容**:
- 最小限のステップでの開始方法
- よく使うコマンド例
- 簡易トラブルシューティング

---

#### `GEMINI3_FILES_SUMMARY.md` (このファイル)
**用途**: 作成されたファイルの概要

---

### 4. 設定ファイル

#### `env_sample.txt`
**用途**: `.env`ファイルのサンプル・テンプレート

**内容**:
- GOOGLE_API_KEY設定例
- ANTHROPIC_API_KEY設定例（オプション）
- 詳細なコメントと取得方法の説明

**使用方法**:
```bash
cp env_sample.txt .env
nano .env  # API Keyを設定
```

---

#### `requirements.txt` (更新)
**変更内容**:
- `python-dotenv>=1.0.0` を追加
- `.env`ファイルサポートを有効化

---

## 🔄 既存ファイルとの関係

### 既存のスクリプトとの違い

| 項目 | `summarize_surveys.py` (既存) | `summarize_surveys_gemini3.py` (新規) |
|------|-------------------------------|---------------------------------------|
| LLMプロバイダー | Claude / Gemini / Ollama | Gemini 3 Pro Preview専用 |
| 設定方法 | 環境変数 | `.env`ファイル |
| Geminiモデル | `gemini-1.5-pro` | `gemini-exp-1206` など3種類 |
| スタンドアロン | いいえ（他ファイルに依存） | はい（単独で動作） |

### 互換性

- 既存の`survey_chunks/`データを使用
- 出力先は別ディレクトリ（`survey_summaries/gemini3/`）
- 既存のスクリプトと併用可能

---

## 📊 ディレクトリ構造

```
survey_analysis/
├── summarize_surveys_gemini3.py  ⭐ メインスクリプト
├── test_gemini3_connection.py    🧪 接続テスト
├── setup_gemini3.sh               🔧 セットアップ
├── README_GEMINI3.md              📖 詳細ドキュメント
├── QUICKSTART_GEMINI3.md          🚀 クイックスタート
├── GEMINI3_FILES_SUMMARY.md       📋 このファイル
├── env_sample.txt                 📄 .envファイルのサンプル
├── .env                           🔑 API Key (自分で作成)
├── requirements.txt               📦 依存パッケージ（更新済み）
│
├── survey_chunks/                 📂 入力データ
│   └── survey_*.json
│
└── survey_summaries/              📂 出力
    ├── gemini3/                   🆕 Gemini 3の結果
    │   └── summaries/
    │       └── *_summary.json
    ├── claude/                    既存（Claude）
    └── gemini/                    既存（Gemini 1.5）
```

---

## 🚀 使い始める手順

### 最小限の手順（5分）

1. **環境をアクティベート**
   ```bash
   conda activate mirai_db_analysis_py3.11
   cd survey_analysis
   ```

2. **セットアップ実行**
   ```bash
   ./setup_gemini3.sh
   ```

3. **API Key設定**
   ```bash
   # サンプルファイルから.envを作成（setup_gemini3.shが自動的にやってくれます）
   # または手動でコピー:
   cp env_sample.txt .env
   
   # .envファイルを編集してAPI Keyを設定
   nano .env
   # GOOGLE_API_KEY=your_key_here と入力
   ```

4. **接続テスト**
   ```bash
   python test_gemini3_connection.py
   ```

5. **実行**
   ```bash
   python summarize_surveys_gemini3.py
   ```

---

## 💡 使用例

### 基本的な使い方

```bash
# デフォルト設定で実行
python summarize_surveys_gemini3.py
```

### 高速処理

```bash
# 高速モデル + 大きいバッチサイズ
python summarize_surveys_gemini3.py --model 2.0-flash-exp --batch-size 30
```

### 詳細な分析

```bash
# 思考プロセス付きモデル + 小さいバッチサイズ
python summarize_surveys_gemini3.py --model 2.0-flash-thinking-exp --batch-size 5
```

### 特定のアンケートのみ

```bash
# 特定のアンケートだけ処理
python summarize_surveys_gemini3.py --survey plan2026
```

---

## 🔧 カスタマイズポイント

### スクリプト内の主要な設定

#### `summarize_surveys_gemini3.py` の設定値

```python
# デフォルトモデル
DEFAULT_GEMINI3_MODEL = "gemini-exp-1206"

# バッチサイズ
DEFAULT_BATCH_SIZE = 10

# APIリトライ設定
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# 要約設定
SUMMARY_MAX_TOKENS = 4096
SUMMARY_TEMPERATURE = 0.7
```

これらの値は必要に応じてスクリプト内で変更可能です。

---

## 📝 注意事項

1. **API使用量**: Google AI APIの無料枠に注意
2. **レート制限**: 大量のリクエストは自動的に待機されます
3. **データの場所**: `survey_chunks/`に処理対象データが必要
4. **出力の上書き**: 同じアンケートを再処理すると結果が上書きされます

---

## 🆘 トラブルシューティング

### よくあるエラー

1. **GOOGLE_API_KEY not found**
   → `.env`ファイルを確認

2. **ModuleNotFoundError: No module named 'dotenv'**
   → `pip install -r requirements.txt`

3. **Rate limit hit**
   → 自動的に待機して再試行されます

4. **No survey files found**
   → `survey_chunks/`ディレクトリを確認

詳細は`README_GEMINI3.md`を参照してください。

---

## 📚 さらに詳しく

- **詳細ドキュメント**: [README_GEMINI3.md](README_GEMINI3.md)
- **クイックスタート**: [QUICKSTART_GEMINI3.md](QUICKSTART_GEMINI3.md)
- **元のスクリプト**: [summarize_surveys.py](summarize_surveys.py)

---

**作成日**: 2025年11月21日  
**対象環境**: Python 3.11+ (conda: mirai_db_analysis_py3.11)  
**必要なAPI**: Google AI API (Gemini)

