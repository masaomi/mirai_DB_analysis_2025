# Amazon Bedrock (Claude Sonnet 4.5) を使ったアンケート要約

このドキュメントでは、Amazon Bedrock経由でClaude Sonnet 4.5を使ってアンケート回答を要約する方法を説明します。

## 必要な環境

- Python 3.11以上
- Conda環境: `mirai_db_analysis_py3.11`
- AWS Bedrock アクセス権限
- AWS認証情報（Bearer TokenまたはAccess Keys）

## セットアップ手順

### 1. Conda環境のアクティベート

```bash
conda activate mirai_db_analysis_py3.11
cd survey_analysis
```

### 2. 必要なパッケージのインストール

```bash
pip install -r requirements.txt
```

### 3. AWS Bedrockのモデルアクセスを有効化

#### AWS Console での設定

1. [AWS Console](https://console.aws.amazon.com/) にログイン
2. Bedrockサービスに移動
3. 左メニューから「Model access」を選択
4. 使用するモデルへのアクセスをリクエスト:
   - **Claude Sonnet 4.5**: Inference Profiles (eu/us)
   - **Claude 3.5 Sonnet**: Direct model access
5. 承認を待つ（通常は即座、Sonnet 4.5は審査が必要な場合あり）

### 4. AWS認証情報の設定

`.env`ファイルを作成してAWS認証情報を設定します：

```bash
# サンプルファイルをコピー
cp env_bedrock_sample.txt .env

# エディタで.envファイルを編集
nano .env
```

#### オプションA: Bearer Token認証（Sonnet 4.5用）

`.env`ファイルの内容：

```bash
AWS_REGION=eu-central-1
AWS_BEARER_TOKEN_BEDROCK=your_bearer_token_here
```

#### オプションB: Access Key認証（Sonnet 3.5など）

`.env`ファイルの内容：

```bash
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

### 5. IAM権限の設定（Access Key使用時）

IAMユーザーに以下のポリシーをアタッチ：

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream"
            ],
            "Resource": "*"
        }
    ]
}
```

または、マネージドポリシー `AmazonBedrockFullAccess` を使用。

### 6. 接続テスト

```bash
python test_bedrock_connection.py
```

✅ が表示されれば成功！

## 使用方法

### 基本的な使い方

```bash
# デフォルトモデル（Claude Sonnet 4.5 EU）で実行
python summarize_surveys_bedrock.py
```

### 利用可能なモデル

以下のモデルが利用可能です：

1. **sonnet-4.5-eu** (デフォルト)
   - モデルID: `eu.anthropic.claude-sonnet-4-5-20250929-v1:0`
   - 最新のClaude Sonnet 4.5
   - Bearer Token認証が必要
   - 推奨モデル

2. **sonnet-4.5-us**
   - モデルID: `us.anthropic.claude-sonnet-4-5-20250929-v1:0`
   - US regionのSonnet 4.5
   - Bearer Token認証が必要

3. **sonnet-3.5**
   - モデルID: `anthropic.claude-3-5-sonnet-20241022-v2:0`
   - Claude 3.5 Sonnet
   - Access Key認証で使用可能

4. **sonnet-3**
   - モデルID: `anthropic.claude-3-sonnet-20240229-v1:0`
   - Claude 3 Sonnet

5. **haiku-3**
   - モデルID: `anthropic.claude-3-haiku-20240307-v1:0`
   - Claude 3 Haiku（高速・低コスト）

### オプション付きの実行例

```bash
# 特定のモデルを指定
python summarize_surveys_bedrock.py --model sonnet-3.5

# 特定のアンケートのみ処理
python summarize_surveys_bedrock.py --survey marumie-shikin

# バッチサイズを変更
python summarize_surveys_bedrock.py --batch-size 20

# 複数オプションの組み合わせ
python summarize_surveys_bedrock.py --model sonnet-4.5-eu --survey plan2026 --batch-size 15
```

### ヘルプの表示

```bash
python summarize_surveys_bedrock.py --help
```

## 出力結果

処理結果は以下のディレクトリに保存されます：

```
survey_summaries/
└── bedrock/
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
  "provider": "bedrock",
  "model": "eu.anthropic.claude-sonnet-4-5-20250929-v1:0",
  "region": "eu-central-1",
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

## トラブルシューティング

### 認証エラー

```
❌ Failed to initialize Bedrock provider
```

**解決方法**: 
1. `.env`ファイルが存在するか確認
2. AWS認証情報が正しく設定されているか確認
3. 接続テストを実行: `python test_bedrock_connection.py`

### モデルアクセスエラー

```
❌ Could not resolve the foundation model
```

**解決方法**:
1. AWS Console > Bedrock > Model accessでモデルアクセスが有効か確認
2. Sonnet 4.5を使用する場合、Inference Profilesへのアクセスが必要
3. Bearer Token認証を使用しているか確認

### IAM権限エラー

```
❌ AccessDeniedException
```

**解決方法**:
1. IAMユーザーに`bedrock:InvokeModel`権限があるか確認
2. `AmazonBedrockFullAccess`ポリシーをアタッチ

### リージョンエラー

```
❌ Model not available in region
```

**解決方法**:
1. Bedrockが利用可能なリージョンを指定（eu-central-1, us-east-1など）
2. `.env`の`AWS_REGION`を確認

## パフォーマンスの最適化

### バッチサイズの調整

- **小さいバッチサイズ (5-10)**: より詳細な分析、処理時間が長い
- **中程度のバッチサイズ (10-20)**: バランスが良い（推奨）
- **大きいバッチサイズ (20-50)**: 高速処理、詳細度が若干低下

### モデルの選択

- **Sonnet 4.5**: 最高品質、やや高コスト
- **Sonnet 3.5**: 高品質でバランスが良い（推奨）
- **Haiku 3**: 高速処理、低コスト

## コスト管理

### 料金体系

Bedrockは使用したトークン数に応じて課金されます：

- **Claude Sonnet 4.5**: 入力 $3/1M tokens, 出力 $15/1M tokens
- **Claude 3.5 Sonnet**: 入力 $3/1M tokens, 出力 $15/1M tokens
- **Claude 3 Haiku**: 入力 $0.25/1M tokens, 出力 $1.25/1M tokens

### コスト削減のヒント

1. バッチサイズを大きくして処理回数を減らす
2. 小規模なアンケートには Haiku 3 を使用
3. `--survey`オプションで特定のアンケートのみ処理

## 注意事項

1. **AWS料金**: Bedrockの使用は従量課金です
2. **処理時間**: アンケートの規模によって処理時間が大きく変わります
3. **リージョン**: Sonnet 4.5はEU/USリージョンでInference Profileとして利用可能
4. **認証方法**: Sonnet 4.5はBearer Token、その他はAccess Keyを推奨

## サポート

問題が発生した場合は、以下を確認してください：

1. Conda環境が正しくアクティベートされているか
2. `.env`ファイルが正しく設定されているか
3. AWS Bedrockのモデルアクセスが有効か
4. IAMユーザーに適切な権限があるか
5. 接続テストを実行: `python test_bedrock_connection.py`

## 関連ドキュメント

- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Claude Models on Bedrock](https://docs.anthropic.com/claude/docs/claude-on-amazon-bedrock)
- [Bedrock Pricing](https://aws.amazon.com/bedrock/pricing/)
- [元のスクリプト](./summarize_surveys.py)

## 参考: test_depth_interview_ai_2025との関連

このスクリプトは`test_depth_interview_ai_2025`プロジェクトのBedrock実装を参考にしています：

- Bearer Token認証のサポート
- Inference Profilesの使用
- Claude Messages API形式のリクエスト
- エラーハンドリングとリトライロジック



















