#!/usr/bin/env python3
"""
Test Gemini 3 Pro Preview API connection.

This script tests if the Google API key is properly configured and
the Gemini 3 Pro Preview API is accessible.

Usage:
    python test_gemini3_connection.py [--model MODEL_NAME]
"""

import os
import argparse
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai


# Load environment variables
load_dotenv()

# Available models
GEMINI3_MODELS = {
    "exp-1206": "gemini-exp-1206",
    "2.0-flash-exp": "gemini-2.0-flash-exp",
    "2.0-flash-thinking-exp": "gemini-2.0-flash-thinking-exp-1219",
}


def test_api_connection(model_name: str = "gemini-exp-1206"):
    """
    Test Gemini 3 API connection.
    
    Args:
        model_name: Model name to test
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    print("\n" + "="*70)
    print("GEMINI 3 PRO PREVIEW 接続テスト")
    print("="*70 + "\n")
    
    # Check API key
    api_key = os.getenv("GOOGLE_API_KEY")
    
    if not api_key:
        print("❌ エラー: GOOGLE_API_KEYが設定されていません")
        print("\n以下を確認してください:")
        print("1. .envファイルが存在するか")
        print("2. .envファイルに以下の形式でAPI Keyが設定されているか:")
        print("   GOOGLE_API_KEY=your_api_key_here")
        print("\nAPI Keyの取得方法:")
        print("   https://aistudio.google.com/app/apikey")
        return False
    
    print(f"✅ GOOGLE_API_KEY: {'*' * 20}{api_key[-4:]}")
    print(f"📋 テストモデル: {model_name}")
    print()
    
    # Configure API
    try:
        genai.configure(api_key=api_key)
        print("✅ Google AI API設定完了")
    except Exception as e:
        print(f"❌ API設定エラー: {e}")
        return False
    
    # Initialize model
    try:
        model = genai.GenerativeModel(model_name)
        print(f"✅ モデル初期化完了: {model_name}")
    except Exception as e:
        print(f"❌ モデル初期化エラー: {e}")
        return False
    
    # Test generation
    print("\n" + "-"*70)
    print("テストプロンプトを送信中...")
    print("-"*70 + "\n")
    
    test_prompt = """以下の3つの意見を要約してください:

1. このサービスは使いやすくて良いと思います
2. もう少し機能が増えると嬉しいです
3. デザインがシンプルで分かりやすい

簡潔に要約してください。"""
    
    try:
        generation_config = genai.types.GenerationConfig(
            max_output_tokens=200,
            temperature=0.7,
        )
        
        response = model.generate_content(
            test_prompt,
            generation_config=generation_config
        )
        
        print("📝 生成されたレスポンス:")
        print("-"*70)
        print(response.text)
        print("-"*70)
        
        # Token usage
        if hasattr(response, 'usage_metadata'):
            print(f"\n📊 使用トークン数:")
            print(f"   入力: {response.usage_metadata.prompt_token_count}")
            print(f"   出力: {response.usage_metadata.candidates_token_count}")
            print(f"   合計: {response.usage_metadata.prompt_token_count + response.usage_metadata.candidates_token_count}")
        
        print("\n✅ API接続テスト成功!")
        print("="*70 + "\n")
        
        return True
        
    except Exception as e:
        print(f"❌ API呼び出しエラー: {e}")
        print("\n考えられる原因:")
        print("1. APIキーが無効または期限切れ")
        print("2. APIの使用制限に達している")
        print("3. ネットワーク接続の問題")
        print("4. モデル名が正しくない")
        return False


def check_environment():
    """Check Python environment and packages."""
    print("\n環境チェック:")
    print("-"*70)
    
    # Python version
    import sys
    print(f"Python バージョン: {sys.version.split()[0]}")
    
    # Check conda environment
    conda_env = os.getenv("CONDA_DEFAULT_ENV")
    if conda_env:
        print(f"Conda 環境: {conda_env}")
        if conda_env != "mirai_db_analysis_py3.11":
            print("⚠️  警告: 推奨環境はmirai_db_analysis_py3.11です")
    else:
        print("⚠️  Conda環境が検出されません")
    
    # Check packages
    print("\nパッケージ:")
    try:
        import google.generativeai
        print(f"  ✅ google-generativeai: {google.generativeai.__version__}")
    except ImportError:
        print("  ❌ google-generativeai: インストールされていません")
    
    try:
        from dotenv import load_dotenv
        print("  ✅ python-dotenv: インストール済み")
    except ImportError:
        print("  ❌ python-dotenv: インストールされていません")
    
    # Check .env file
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        print(f"\n✅ .envファイル: 存在します ({env_file})")
    else:
        print(f"\n⚠️  .envファイル: 存在しません ({env_file})")
        print("   setup_gemini3.shを実行してセットアップしてください")
    
    print("-"*70 + "\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test Gemini 3 Pro Preview API connection",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--model',
        choices=list(GEMINI3_MODELS.keys()),
        default='exp-1206',
        help='Model to test (default: exp-1206)'
    )
    
    parser.add_argument(
        '--skip-env-check',
        action='store_true',
        help='Skip environment check'
    )
    
    args = parser.parse_args()
    
    # Environment check
    if not args.skip_env_check:
        check_environment()
    
    # Get model name
    model_name = GEMINI3_MODELS[args.model]
    
    # Test connection
    success = test_api_connection(model_name)
    
    if success:
        print("\n🎉 すべてのテストに合格しました!")
        print("summarize_surveys_gemini3.pyを実行する準備が整いました。")
        return 0
    else:
        print("\n❌ テストが失敗しました")
        print("上記のエラーメッセージを確認して問題を解決してください。")
        return 1


if __name__ == "__main__":
    exit(main())





















