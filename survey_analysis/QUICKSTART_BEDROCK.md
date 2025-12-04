# Amazon Bedrock (Claude Sonnet 4.5) クイックスタートガイド

このガイドでは、最短5分でAmazon Bedrock（Claude Sonnet 4.5）を使ったアンケート要約を開始できます。

## 📋 事前準備

1. AWSアカウントとBedrock利用権限
2. AWS認証情報（Bearer TokenまたはAccess Keys）
3. Conda環境: `mirai_db_analysis_py3.11`

## 🚀 セットアップ（5分）

### ステップ1: 環境のアクティベート

```bash
conda activate mirai_db_analysis_py3.11
cd survey_analysis
```

### ステップ2: パッケージのインストール

```bash
pip install -r requirements.txt
```

### ステップ3: Bedrockモデルアクセスの有効化

1. [AWS Console](https://console.aws.amazon.com/) → Bedrock → Model access
2. 使用するモデルへのアクセスをリクエスト
   - **Claude Sonnet 4.5**: Inference Profiles
   - **Claude 3.5 Sonnet**: Direct model access
3. 承認を待つ

### ステップ4: AWS認証情報の設定

サンプルファイルをコピー：

```bash
cp env_bedrock_sample.txt .env
nano .env
```

#### パターンA: Bearer Token（Sonnet 4.5用）

```bash
AWS_REGION=eu-central-1
AWS_BEARER_TOKEN_BEDROCK=your_bearer_token_here
```

#### パターンB: Access Keys（Sonnet 3.5など）

```bash
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

保存して終了（`Ctrl+X` → `Y` → `Enter`）

### ステップ5: 接続テスト

```bash
python test_bedrock_connection.py
```

✅ が表示されれば成功！

## 🎯 実行方法

### 基本的な実行

```bash
python summarize_surveys_bedrock.py
```

### よく使うオプション

```bash
# 特定のアンケートのみ処理
python summarize_surveys_bedrock.py --survey marumie-shikin

# Claude 3.5 Sonnetを使用
python summarize_surveys_bedrock.py --model sonnet-3.5

# バッチサイズを調整（処理速度向上）
python summarize_surveys_bedrock.py --batch-size 20
```

## 📊 結果の確認

処理が完了すると、以下の場所に結果が保存されます：

```
survey_summaries/bedrock/summaries/
├── アンケート1_summary.json
├── アンケート2_summary.json
└── ...
```

## 💡 Tips

### 処理が遅い場合

```bash
# バッチサイズを大きくする
python summarize_surveys_bedrock.py --batch-size 30
```

### コストを抑えたい場合

```bash
# Haiku 3を使用（高速・低コスト）
python summarize_surveys_bedrock.py --model haiku-3
```

### 高品質な分析が必要な場合

```bash
# Sonnet 4.5を使用（最高品質）
python summarize_surveys_bedrock.py --model sonnet-4.5-eu
```

## 🔧 トラブルシューティング

### エラー: AWS credentials not found

**解決方法**: `.env`ファイルが正しく設定されているか確認

```bash
cat .env
```

### エラー: AccessDeniedException

**解決方法**: IAMユーザーに権限を追加

1. AWS Console → IAM → Users
2. ユーザーを選択
3. Permissions → Add permissions
4. `AmazonBedrockFullAccess`ポリシーをアタッチ

### エラー: Model not found

**解決方法**: Bedrockモデルアクセスを確認

1. AWS Console → Bedrock → Model access
2. 使用するモデルが「Access granted」になっているか確認

### エラー: ModuleNotFoundError: No module named 'boto3'

**解決方法**: パッケージを再インストール

```bash
pip install -r requirements.txt
```

## 📚 さらに詳しい情報

- [詳細ドキュメント](README_BEDROCK.md)
- [元のスクリプト](summarize_surveys.py)

## 💰 コスト見積もり

### 料金例（Claude Sonnet 4.5）

- 入力: $3/1M tokens
- 出力: $15/1M tokens

### 実際のコスト例

- 小規模アンケート（100回答）: 約 $0.10 - $0.50
- 中規模アンケート（500回答）: 約 $0.50 - $2.00
- 大規模アンケート（2000回答）: 約 $2.00 - $10.00

※実際のコストは質問数や回答の長さによって変動します

## 🆘 サポート

問題が解決しない場合は、以下を確認してください：

1. ✅ Conda環境がアクティブか

   ```bash
   echo $CONDA_DEFAULT_ENV
   # → mirai_db_analysis_py3.11 と表示されるはず
   ```

2. ✅ AWS認証情報が正しく設定されているか

   ```bash
   python test_bedrock_connection.py
   ```

3. ✅ survey_chunks/にデータが存在するか

   ```bash
   ls -la survey_chunks/
   ```

4. ✅ Bedrockモデルアクセスが有効か
   - AWS Console → Bedrock → Model access

---

**🎉 準備完了！ アンケート分析を始めましょう！**












