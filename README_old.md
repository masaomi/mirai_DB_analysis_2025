# AIアンケートデータ解析ツール

このプロジェクトは、AIにより取得した自由記述式アンケートデータを多角的に解析するためのツールセットです。

## データ概要

- **バックアップファイル**: `backup-2025-11-14T03-19-14.json` / `.sql`
- **データ種別**: PostgreSQL形式のデータベースバックアップ
- **データ内容**: インタビュー/アンケートシステムのデータ

### データ構造

- `interview_configs`: 12件（インタビュー設定）
- `interview_sessions`: 15,341件（セッション）
- `messages`: 142,237件（メッセージ、うちユーザー回答65,318件）
- `aggregate_reports`: 206件（集計レポート）

### 主要トピック

1. 国会議員定数削減に関するインタビュー (6,604セッション)
2. 「人工知能基本計画」に関するご意見のヒアリング (4,561セッション)
3. 『チームみらい』の今後の1年の計画（１年プラン）のインタビュー (2,403セッション)
4. 船荷証券の電子化法案に関するインタビュー (888セッション)
5. その他（政治資金、プロダクト開発など）

## 解析ツール

### 1. 基本分析 (`analyze_data.py`)

データの基本統計、トピック別分析、キーワード抽出などを行います。

```bash
python3 analyze_data.py
```

出力: `analysis_report.txt`

### 2. データビジュアル化 (`visualize_data.py`)

以下の可視化を生成します：
- トピック別のセッション数・回答数の分布
- 回答文字数の分布
- セッション完了率
- 時系列での回答数の推移
- ワードクラウド

```bash
python3 visualize_data.py
```

**必要なライブラリ**:
```bash
pip install matplotlib seaborn wordcloud pandas
```

出力: `visualizations/` ディレクトリに各種グラフ

### 3. 回答のカテゴリ化 (`categorize_responses.py`)

回答を以下の観点でカテゴリ化します：
- 文字数による分類（短文/中程度/長文）
- 感情分析による分類（ポジティブ/ネガティブ/ニュートラル）
- キーフレーズ抽出
- クラスタリング（scikit-learn使用時）

```bash
python3 categorize_responses.py
```

**必要なライブラリ**（オプション）:
```bash
pip install scikit-learn  # クラスタリング用
pip install mecab-python3  # 日本語形態素解析用
```

### 4. AIエージェントによる議論 (`ai_agent_discussion.py`)

過去の有名人（プラトン、孔子、マキャベリ、ルソー、ミル、福澤諭吉、尾崎行雄など）のAIエージェントを召喚し、各トピックの回答を異なる視点から分析・議論するためのプロンプトを生成します。

```bash
python3 ai_agent_discussion.py
```

出力: `discussion_prompts_{topic_slug}.txt`

生成されたプロンプトをLLM（ChatGPT、Claude等）に入力することで、異なる思想・立場からの分析を取得できます。

### 5. Survey RAG Chat AI (`survey_rag_app/`)

アンケート回答を背景知識として持つRAG（Retrieval-Augmented Generation）チャットAIです。質問に対してアンケートデータから関連する回答を検索し、それを基に回答を生成します。

#### 特徴
- **ローカルLLM対応**: Ollama（デフォルト: gpt-oss:20b）を使用したローカル実行
- **クラウドLLM対応**: Amazon Bedrockのモデルも選択可能
- **ブラウザベースUI**: Streamlitで動作するチャット画面
- **RAG機能**: ChromaDBとHuggingFace Embeddingsを使用したベクトル検索

#### セットアップ

1. **依存パッケージのインストール**
   ```bash
   cd survey_rag_app
   pip install -r requirements.txt
   ```

2. **データの取り込み**（初回のみ）
   ```bash
   python ingest_data.py
   ```
   
   このステップで、`backup-2025-11-14T03-19-14.json`からアンケート回答を抽出し、ベクトルデータベース（`chroma_db/`）を作成します。

3. **環境変数の設定**（Amazon Bedrock使用時のみ）
   
   `.env`ファイルを作成し、以下の内容を記述：
   ```
   AWS_ACCESS_KEY_ID=your_access_key_id
   AWS_SECRET_ACCESS_KEY=your_secret_access_key
   AWS_DEFAULT_REGION=us-east-1
   ```

#### 使用方法

1. **アプリの起動**
   ```bash
   streamlit run app.py
   ```
   
   または、特定のPythonバージョンを指定する場合：
   ```bash
   python3.10 -m streamlit run app.py
   ```

2. **ブラウザでアクセス**
   
   ブラウザで `http://localhost:8501` にアクセス

3. **LLMの設定**
   
   サイドバーから以下を設定：
   
   **Ollama (Local)を使用する場合:**
   - Base URL: `http://localhost:11434`（デフォルト）
   - Model Name: `gpt-oss:20b`（デフォルト）
   - ⚠️ 事前にOllamaをインストールし、モデルをプルしておく必要があります
     ```bash
     ollama pull gpt-oss:20b
     ```
   
   **Amazon Bedrockを使用する場合:**
   - Model ID: 使用したいBedrockモデルを選択（例: `anthropic.claude-3-sonnet-20240229-v1:0`）
   - Region: AWSリージョンを指定（デフォルト: `us-east-1`）
   - ⚠️ AWSの認証情報（`.env`ファイル）が必要です

4. **チャット開始**
   
   画面下部のチャット入力欄から質問を入力してください。例：
   - 「国会議員定数削減についてどんな意見がありましたか？」
   - 「AIに関する懸念点を教えてください」
   - 「チームみらいの活動について、どのような提案がありましたか？」

#### トラブルシューティング

- **Ollamaが接続できない場合**
  - Ollamaが起動しているか確認: `ollama list`
  - モデルがプルされているか確認: `ollama pull gpt-oss:20b`
  - Base URLが正しいか確認（デフォルト: `http://localhost:11434`）

- **Amazon Bedrockが使えない場合**
  - `.env`ファイルのAWS認証情報が正しいか確認
  - 使用するリージョンでBedrockモデルが利用可能か確認
  - AWSアカウントにBedrockの利用権限があるか確認

- **"chroma_db not found"エラーが出る場合**
  - `ingest_data.py`を実行してベクトルデータベースを作成してください

## 推奨される解析方法

### 1. カテゴリ化分析
- トピックごとの回答をクラスタリング
- 感情分析によるポジティブ/ネガティブ分類
- テーマ別の自動分類（メリット、懸念、提案など）

### 2. ビジュアル化
- トピック別の回答数・セッション数の棒グラフ
- 回答文字数の分布ヒストグラム
- キーワードのワードクラウド
- 時系列での回答数の推移
- セッション完了率の可視化

### 3. 深掘り分析
- トピック間の回答パターンの比較
- 長文回答と短文回答の内容の違い
- セッションの完了率と回答品質の関係

### 4. AIエージェントによる議論
- 過去の有名人（政治家、思想家）のAIエージェントを召喚
- 各トピックの回答を彼らの視点で分析・議論
- 異なる立場からの意見の対比

### 5. テキストマイニング
- 共起ネットワーク分析（キーワードの関連性）
- トピックモデリング（LDA等）
- 感情分析（ポジティブ/ネガティブ/ニュートラル）
- 要約生成（各トピックの主要な意見の抽出）

### 6. RAGチャットAIによるインタラクティブな分析
- アンケート回答を背景知識として持つAIとの対話
- 自然言語でデータを検索・質問
- 関連する回答を自動的に抽出して文脈を提供

## セットアップ

### 必要なPythonパッケージ

基本機能:
```bash
pip install matplotlib seaborn
```

全機能を使用する場合:
```bash
pip install matplotlib seaborn wordcloud pandas scikit-learn
```

日本語テキスト分析を強化する場合:
```bash
pip install mecab-python3
```

## 使用例

### 基本的な分析フロー

1. **データの概要を把握**
   ```bash
   python3 analyze_data.py
   ```

2. **ビジュアル化**
   ```bash
   python3 visualize_data.py
   ```

3. **カテゴリ化**
   ```bash
   python3 categorize_responses.py
   ```

4. **AIエージェント議論の準備**
   ```bash
   python3 ai_agent_discussion.py
   ```

### 特定のトピックを分析する場合

各スクリプトは、コード内でトピックを指定することで特定のトピックに絞った分析が可能です。

## 出力ファイル

- `analysis_report.txt`: 基本分析レポート
- `visualizations/`: 各種グラフ・チャート
- `discussion_prompts_{topic}.txt`: AIエージェント用プロンプト

## 注意事項

- JSONファイルは約164万行の大きなファイルです。メモリ使用量に注意してください。
- 一部の機能（クラスタリング、高度なテキスト分析）には追加のライブラリが必要です。
- 日本語フォントの設定により、グラフの日本語表示が正しく表示されない場合があります。

## 今後の拡張予定

- [ ] より高度な感情分析（BERT等のモデル使用）
- [ ] トピックモデリング（LDA）の実装
- [ ] 共起ネットワーク分析
- [x] インタラクティブなダッシュボード（Streamlit等）→ **実装済み（Survey RAG Chat AI）**
- [ ] データベースへの直接接続機能
- [ ] RAGチャットAIの機能拡張（会話履歴の保存、エクスポート機能など）
