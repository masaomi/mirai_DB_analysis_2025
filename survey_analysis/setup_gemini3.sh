#!/bin/bash
# Setup script for Gemini 3 Pro Preview survey analysis

echo "=========================================="
echo "Gemini 3 Pro Preview セットアップ"
echo "=========================================="
echo ""

# Check if conda environment is activated
if [[ "$CONDA_DEFAULT_ENV" != "mirai_db_analysis_py3.11" ]]; then
    echo "⚠️  警告: mirai_db_analysis_py3.11 環境がアクティブではありません"
    echo "以下のコマンドを実行してください:"
    echo "  conda activate mirai_db_analysis_py3.11"
    echo ""
    read -p "続行しますか? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Install requirements
echo "📦 必要なパッケージをインストール中..."
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ パッケージのインストールに失敗しました"
    exit 1
fi

echo "✅ パッケージのインストール完了"
echo ""

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 .envファイルを作成中..."
    if [ -f env_sample.txt ]; then
        cp env_sample.txt .env
        echo "✅ .envファイルを作成しました（env_sample.txtからコピー）"
    else
        cat > .env << 'EOF'
# Google AI API Configuration
# Get your API key from: https://aistudio.google.com/app/apikey
GOOGLE_API_KEY=

# Optional: Anthropic API (for Claude)
ANTHROPIC_API_KEY=
EOF
        echo "✅ .envファイルを作成しました"
    fi
    echo ""
    echo "⚠️  重要: .envファイルにGoogle API Keyを設定してください"
    echo "   1. https://aistudio.google.com/app/apikey でAPIキーを取得"
    echo "   2. .envファイルを編集してGOOGLE_API_KEYに設定"
    echo ""
    echo "編集方法:"
    echo "  nano .env"
    echo "  または"
    echo "  vim .env"
    echo ""
else
    echo "✅ .envファイルは既に存在します"
    echo ""
fi

# Create output directory
echo "📁 出力ディレクトリを作成中..."
mkdir -p survey_summaries/gemini3/summaries
echo "✅ 出力ディレクトリを作成しました"
echo ""

# Check if survey chunks exist
if [ ! -d "survey_chunks" ] || [ -z "$(ls -A survey_chunks)" ]; then
    echo "⚠️  警告: survey_chunks/ ディレクトリが空です"
    echo "   先にextract_surveys.pyを実行してください:"
    echo "   python extract_surveys.py"
    echo ""
fi

echo "=========================================="
echo "✨ セットアップ完了!"
echo "=========================================="
echo ""
echo "次のステップ:"
echo "1. .envファイルにGoogle API Keyを設定"
echo "2. スクリプトを実行:"
echo "   python summarize_surveys_gemini3.py"
echo ""
echo "詳細はREADME_GEMINI3.mdを参照してください"

