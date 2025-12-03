# Gemini 3 Pro Preview クイックスタートガイド

このガイドでは、最短5分でGemini 3 Pro Previewを使ったアンケート要約を開始できます。

## 📋 事前準備

1. Google AI API Key（[取得はこちら](https://aistudio.google.com/app/apikey)）
2. Conda環境: `mirai_db_analysis_py3.11`

## 🚀 セットアップ（5分）

### ステップ1: 環境のアクティベート

```bash
conda activate mirai_db_analysis_py3.11
cd survey_analysis
```

### ステップ2: セットアップスクリプトの実行

```bash
./setup_gemini3.sh
```

このスクリプトが自動的に以下を実行します：
- 必要なパッケージのインストール
- `.env`ファイルの作成
- 出力ディレクトリの作成

### ステップ3: API Keyの設定

方法1: サンプルファイルからコピー
```bash
cp env_sample.txt .env
nano .env
```

方法2: 直接作成
```bash
nano .env
```

以下のように設定：
```
GOOGLE_API_KEY=あなたのAPIキーをここに入力
```

保存して終了（nano: `Ctrl+X` → `Y` → `Enter`）

### ステップ4: 接続テスト

```bash
python test_gemini3_connection.py
```

✅ が表示されれば成功！

## 🎯 実行方法

### 基本的な実行

```bash
python summarize_surveys_gemini3.py
```

### よく使うオプション

```bash
# 特定のアンケートのみ処理
python summarize_surveys_gemini3.py --survey plan2026

# 高速モデルを使用
python summarize_surveys_gemini3.py --model 2.0-flash-exp

# バッチサイズを調整（処理速度向上）
python summarize_surveys_gemini3.py --batch-size 20
```

## 📊 結果の確認

処理が完了すると、以下の場所に結果が保存されます：

```
survey_summaries/gemini3/summaries/
├── アンケート1_summary.json
├── アンケート2_summary.json
└── ...
```

## 💡 Tips

### 処理が遅い場合
```bash
# バッチサイズを大きくする
python summarize_surveys_gemini3.py --batch-size 30
```

### 詳細な分析が必要な場合
```bash
# 思考プロセス付きモデルを使用
python summarize_surveys_gemini3.py --model 2.0-flash-thinking-exp
```

### 特定のアンケートだけ処理したい
```bash
# アンケートのスラッグを指定
python summarize_surveys_gemini3.py --survey your-survey-slug
```

## 🔧 トラブルシューティング

### エラー: GOOGLE_API_KEY not found

**解決方法**: `.env`ファイルが正しく設定されているか確認
```bash
cat .env
```

### エラー: Rate limit hit

**説明**: APIのレート制限に達しました。スクリプトが自動的に待機して再試行します。

### エラー: ModuleNotFoundError

**解決方法**: パッケージを再インストール
```bash
pip install -r requirements.txt
```

## 📚 さらに詳しい情報

- [詳細ドキュメント](README_GEMINI3.md)
- [元のスクリプト](summarize_surveys.py)

## 🆘 サポート

問題が解決しない場合は、以下を確認してください：

1. ✅ Conda環境がアクティブか
   ```bash
   echo $CONDA_DEFAULT_ENV
   # → mirai_db_analysis_py3.11 と表示されるはず
   ```

2. ✅ API Keyが正しく設定されているか
   ```bash
   python test_gemini3_connection.py
   ```

3. ✅ survey_chunks/にデータが存在するか
   ```bash
   ls -la survey_chunks/
   ```

---

**🎉 準備完了！ アンケート分析を始めましょう！**

