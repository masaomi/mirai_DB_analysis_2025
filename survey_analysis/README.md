# アンケート回答分析レポート

このディレクトリには、各種アンケートの自由記述回答をカテゴリ化・可視化したパイチャートと、LLMを使用した要約レポートが含まれています。

## 🆕 新機能: LLM要約パイプライン

**Claude Sonnet 4.5**、**Gemini 3 Pro**、**Ollama (gpt-oss20b)** を使用して、各アンケートの自由回答を自動要約できます。大規模データを効率的に処理し、Markdown/HTML/PDF形式のレポートを生成します。

### 対応LLM
- **Claude Sonnet 4.5** - 高品質な要約（API費用あり）
- **Gemini 3 Pro** - 高品質な要約（API費用あり）
- **Ollama (gpt-oss20b)** - ローカル実行・無料（要約品質は中程度）

## 📁 ファイル構成

```
survey_analysis/
├── README.md                           # このファイル
├── requirements.txt                    # Pythonパッケージ依存関係
│
├── # 🆕 LLM要約パイプライン
├── config.py                           # 設定ファイル
├── llm_providers.py                    # LLM統一インターフェース
├── extract_surveys.py                  # データ抽出スクリプト
├── summarize_surveys.py                # LLM要約スクリプト
├── generate_reports.py                 # Markdownレポート生成
├── convert_to_formats.py               # HTML/PDF変換
├── run_analysis_pipeline.py            # メインパイプライン
│
├── survey_chunks/                      # 抽出されたアンケートデータ
│   ├── survey_*.json
│   └── ...
│
├── survey_summaries/                   # LLM要約レポート
│   ├── claude/
│   │   └── summaries/                  # Claude生成レポート
│   │       ├── *.md, *.html, *.pdf
│   │       └── index.md
│   └── gemini/
│       └── summaries/                  # Gemini生成レポート
│           ├── *.md, *.html, *.pdf
│           └── index.md
│
├── # パイチャート分析（既存機能）
├── index.html                          # 分析結果の一覧ページ
├── create_pie_charts.py                # 分析スクリプト
├── pie_chart_*.png                     # 各種パイチャート
└── ...
```

## 🚀 使い方

### 1. LLM要約パイプライン（推奨）

#### 初期セットアップ

```bash
# 依存パッケージをインストール
pip install -r requirements.txt

# API キーを設定（Claude/Geminiを使う場合）
export ANTHROPIC_API_KEY="your-anthropic-api-key"
export GOOGLE_API_KEY="your-google-api-key"

# Ollamaのセットアップ（ローカルLLMを使う場合）
# 1. Ollamaをインストール
brew install ollama  # macOS
# または https://ollama.ai/ からダウンロード

# 2. Ollamaサーバーを起動
ollama serve

# 3. gpt-oss20bモデルをダウンロード（初回のみ、別ターミナルで）
ollama pull gpt-oss20b

# 4. モデルが利用可能か確認
ollama list
```

#### 完全パイプラインの実行

```bash
# 両方のクラウドLLMで要約を生成（Claude & Gemini）
python run_analysis_pipeline.py

# Ollama（ローカル）のみで実行
python run_analysis_pipeline.py --llm ollama

# 3つすべてのLLMで実行（比較用）
python run_analysis_pipeline.py --llm all

# Claude のみで実行
python run_analysis_pipeline.py --llm claude

# Gemini のみで実行
python run_analysis_pipeline.py --llm gemini

# 別のOllamaモデルを指定
python run_analysis_pipeline.py --llm ollama --model llama3.1:8b

# HTML のみ生成（PDF スキップ）
python run_analysis_pipeline.py --formats html

# 既存の抽出データを使用（抽出ステップをスキップ）
python run_analysis_pipeline.py --skip-extraction
```

#### 個別ステップの実行

```bash
# Step 1: データ抽出（アンケート毎に分割）
python extract_surveys.py

# Step 2: LLM要約
python summarize_surveys.py --llm both --batch-size 10
python summarize_surveys.py --llm ollama --batch-size 10  # Ollamaの場合
python summarize_surveys.py --llm all --batch-size 10     # 全LLM比較

# Step 3: Markdownレポート生成
python generate_reports.py --llm both
python generate_reports.py --llm ollama  # Ollamaの場合

# Step 4: HTML/PDF変換
python convert_to_formats.py --llm both --formats html pdf
python convert_to_formats.py --llm ollama --formats html pdf  # Ollamaの場合

# スマート分割の分析（オプション）
python smart_splitter.py  # 大規模アンケートを自動分析
```

#### 生成されるレポート

```
survey_summaries/
├── claude/
│   └── summaries/
│       ├── index.md           # インデックスページ
│       ├── survey_name.md     # Markdownレポート
│       ├── survey_name.html   # HTMLレポート
│       └── survey_name.pdf    # PDFレポート
├── gemini/
│   └── summaries/
│       ├── index.md
│       ├── survey_name.md
│       ├── survey_name.html
│       └── survey_name.pdf
└── ollama/
    └── summaries/
        ├── index.md
        ├── survey_name.md
        ├── survey_name.html
        └── survey_name.pdf
```

### 2. パイチャート分析（既存機能）

#### 分析結果を見る

1. **index.htmlをブラウザで開く**
   ```bash
   open index.html
   ```
   または、ファイルをダブルクリックしてブラウザで開きます。

2. パイチャートをクリックすると拡大表示されます。

#### 再分析を実行する

データが更新された場合、以下のコマンドで再分析できます：

```bash
# conda環境をアクティベート
conda activate mirai_db_analysis_py3.10

# スクリプトを実行
python create_pie_charts.py
```

## 📊 分析対象データ

- **データソース**: `backup-2025-11-14T03-19-14.json`
- **総回答数**: 62,692件
- **分析アンケート数**: 12種類
- **分析日**: 2025年11月20日

### 分析対象アンケート一覧

| アンケート名 | 回答数 | 主要カテゴリ |
|------------|--------|------------|
| チームみらい1年プラン（公開版） | 25,180 | DX推進、透明性、選挙戦略 |
| 定数削減議論 | 15,743 | 政治・政策、賛否両論 |
| AIプラン | 14,762 | 期待、課題、提案 |
| 船荷証券の電子化 | 2,887 | 賛成、セキュリティ、コスト |
| チームみらい1年プラン | 2,453 | DX、透明性、選挙 |
| みらい議会インタビュー | 783 | 政治・政策、期待 |
| まる見え政治資金（ユーザー） | 645 | 政治、透明性、期待 |
| プロダクトリサーチ | 91 | 課題、提案 |
| カスタマーフィードバック | 53 | 期待、提案 |
| まる見え政治資金（開発者） | 40 | 政治、透明性 |

## 🎯 カテゴリ化の方針

### チームみらい関連アンケート
- **選挙・議席獲得**: 議席、選挙、候補などのキーワード
- **DX・デジタル化**: デジタル、システム、IT、オンラインなど
- **透明性・情報公開**: 透明、公開、見える化、可視化など
- **政治資金の透明化**: 政治資金、献金、お金、資金など
- **汚職・不正の撲滅**: 汚職、不正、腐敗、癒着など
- **国民生活の改善**: 国民、庶民、市民、生活、暮らしなど
- **平和・安全保障**: 平和、戦争、防衛、安全保障など
- **その他の意見**: 上記に該当しない意見

### 船荷証券の電子化
- **賛成・肯定的**: 賛成、良い、メリット、効率など
- **反対・否定的**: 反対、懸念、心配、リスクなど
- **セキュリティ関連**: セキュリティ、安全、保護など
- **コスト関連**: コスト、費用、経費など
- **実務・運用面**: 実務、実装、運用、導入など

### その他のアンケート
- **政治・政策関連**: 政治、政策、議員などのキーワード
- **透明性・情報公開**: 透明性、情報公開、DXなど
- **期待・要望**: ポジティブな意見や期待
- **課題・懸念**: 課題や懸念事項
- **具体的な提案**: 実装や改善の具体提案
- **その他**: 分類外の意見

## 🔧 技術情報

### LLM要約パイプライン

#### 使用技術
- **プログラミング言語**: Python 3.8+
- **LLMプロバイダー**:
  - Claude Sonnet 4.5 (Anthropic) - クラウドAPI
  - Gemini 3 Pro (Google) - クラウドAPI
  - Ollama (gpt-oss20b) - ローカル実行
- **主要ライブラリ**:
  - `anthropic` - Claude API
  - `google-generativeai` - Gemini API
  - `requests` - Ollama API通信
  - `markdown` - Markdown処理
  - `weasyprint` - PDF生成
  - `tqdm` - プログレスバー

#### 処理フロー
1. **抽出**: JSONファイルからアンケート毎にデータを分割
2. **スマート分割**: 大規模アンケートを自動分析し、最適なバッチサイズを決定
3. **要約**: 各質問の回答をバッチ処理で段階的に要約
   - Level 1: 小バッチ要約（10-50件）
   - Level 2: 中バッチ統合（複数の小バッチ）
   - Level 3: 最終統合要約
4. **生成**: Markdown → HTML → PDF の順で変換
5. **出力**: Claude/Gemini/Ollama別にレポートを保存

#### バッチ処理の仕組み
- 大量の回答を10-20件ずつのバッチに分割
- 各バッチを個別に要約
- すべてのバッチ要約を統合して最終要約を生成
- トークン制限を超えないように自動調整

#### PDF生成の注意
PDF生成には以下のシステム依存関係が必要です：

**macOS**:
```bash
brew install cairo pango gdk-pixbuf libffi
```

**Ubuntu/Debian**:
```bash
sudo apt-get install python3-cffi python3-brotli libpango-1.0-0 libpangoft2-1.0-0
```

詳細は [WeasyPrint documentation](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation) を参照してください。

#### Ollama使用時の注意点

**利点**:
- 完全無料（APIコストなし）
- オフライン実行可能
- プライバシー保護（データが外部に送信されない）
- 高速応答（ローカル処理）

**制限事項**:
- 要約品質はClaude/Geminiより劣る場合がある
- 大量のメモリ使用（8GB以上推奨）
- GPUがあると高速化
- モデルダウンロードに時間がかかる（初回のみ）

**トラブルシューティング**:

```bash
# Ollamaサーバーが起動しているか確認
curl http://localhost:11434/api/tags

# モデルがダウンロードされているか確認
ollama list

# ログを確認
ollama serve  # ターミナルでログが表示される

# モデルを再ダウンロード
ollama rm gpt-oss20b
ollama pull gpt-oss20b
```

### パイチャート分析

#### 使用技術
- **プログラミング言語**: Python 3.10
- **データ処理**: JSON
- **可視化ライブラリ**: Matplotlib
- **日本語フォント**: Hiragino Sans, Yu Gothic, Meiryo
- **画像解像度**: 300 DPI

### データ処理フロー
1. JSONデータからセッション情報とメッセージを抽出
2. ユーザー回答（role: "user"）のみを抽出
3. テスト回答や意味のない短文を除外
4. アンケートの種類（slug）別に回答を分類
5. 各アンケートに適したカテゴリ化ルールを適用
6. カテゴリ別の回答数を集計
7. パイチャートを生成

### 除外データ
以下のような回答は分析から除外されています：
- 3文字未満の回答
- テスト用の回答（"test", "ああああ", "a", "aa", "aaa"など）
- 意味のない文字列

## 📝 注意事項

### カテゴリ化の限界
- カテゴリ化は自動化されており、キーワードベースで判定しています
- 一つの回答が複数のキーワードを含む場合、最初にマッチしたカテゴリに分類されます
- より高度な分析にはLLM APIを使用することも可能です

### データの解釈
- 「その他」カテゴリには、短い回答や特定のキーワードが含まれない回答が含まれます
- 回答の質や文脈は考慮されていません（キーワードの有無のみで判定）
- カテゴリの分布は参考情報として活用してください

## 💡 主要な発見

### 1. チームみらい関連（合計27,633回答）
- 最も多くの回答が集まったテーマ
- DX推進と透明性向上への期待が特に高い
- 具体的な政策提案や選挙戦略に関する意見が多数

### 2. 定数削減議論（15,743回答）
- 活発な議論が展開されている
- 政治・政策に関する意見が多く、賛成・反対の両論が見られる

### 3. 船荷証券の電子化（2,887回答）
- 専門的なテーマながら多くの回答
- 賛成意見が多いものの、セキュリティやコストへの懸念も具体的

### 4. プロダクト開発系
- みらい議会やまる見え政治資金に対して具体的な改善提案が多数
- ユーザー体験の向上に関する意見が目立つ

## 📧 お問い合わせ

このレポートや分析手法について質問がある場合は、開発チームまでお問い合わせください。

---

**作成日**: 2025年11月20日  
**最終更新**: 2025年11月20日



