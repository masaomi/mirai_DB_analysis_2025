#!/usr/bin/env python3
"""
Test Amazon Bedrock API connection.

This script tests if AWS credentials are properly configured and
Amazon Bedrock Claude models are accessible.

Usage:
    python test_bedrock_connection.py [--model MODEL_KEY]
"""

import os
import argparse
from pathlib import Path
from dotenv import load_dotenv
import boto3
import json


# Load environment variables
load_dotenv()

# Available models
BEDROCK_MODELS = {
    "sonnet-4.5-eu": "eu.anthropic.claude-sonnet-4-5-20250929-v1:0",
    "sonnet-4.5-us": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    "sonnet-3.5": "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "sonnet-3": "anthropic.claude-3-sonnet-20240229-v1:0",
    "haiku-3": "anthropic.claude-3-haiku-20240307-v1:0",
}


def test_bedrock_connection(model_key: str = "sonnet-4.5-eu"):
    """
    Test Bedrock API connection.
    
    Args:
        model_key: Model key to test
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    print("\n" + "="*70)
    print("AMAZON BEDROCK 接続テスト")
    print("="*70 + "\n")
    
    # Get model ID
    model_id = BEDROCK_MODELS.get(model_key)
    if not model_id:
        print(f"❌ Unknown model key: {model_key}")
        print(f"Available models: {', '.join(BEDROCK_MODELS.keys())}")
        return False
    
    # Check AWS credentials
    region = os.getenv("AWS_REGION")
    bearer_token = os.getenv("AWS_BEARER_TOKEN_BEDROCK")
    access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    
    if not region:
        print("❌ エラー: AWS_REGIONが設定されていません")
        print("\n.envファイルに以下を設定してください:")
        print("   AWS_REGION=eu-central-1")
        return False
    
    print(f"✅ AWS_REGION: {region}")
    print(f"📋 テストモデル: {model_id}")
    
    # Check authentication method
    use_bearer = bool(bearer_token)
    use_access_key = bool(access_key_id and secret_access_key)
    
    if use_bearer:
        print(f"✅ Bearer Token: {'*' * 20}...{bearer_token[-4:]}")
        print("🔐 認証方法: Bearer Token (Inference Profile用)")
    elif use_access_key:
        print(f"✅ AWS_ACCESS_KEY_ID: {access_key_id}")
        print(f"✅ AWS_SECRET_ACCESS_KEY: {'*' * 20}...{secret_access_key[-4:]}")
        print("🔐 認証方法: Access Keys (Direct Model Access用)")
    else:
        print("❌ エラー: AWS認証情報が設定されていません")
        print("\n.envファイルに以下のいずれかを設定してください:")
        print("\n1. Bearer Token認証 (Sonnet 4.5用):")
        print("   AWS_BEARER_TOKEN_BEDROCK=your_bearer_token")
        print("\n2. Access Key認証 (Sonnet 3.5など):")
        print("   AWS_ACCESS_KEY_ID=your_access_key")
        print("   AWS_SECRET_ACCESS_KEY=your_secret_key")
        return False
    
    print()
    
    # Initialize Bedrock client
    try:
        if use_bearer:
            client = boto3.client('bedrock-runtime', region_name=region)
            print("✅ Bedrockクライアント初期化完了 (Bearer Token)")
        else:
            client = boto3.client(
                'bedrock-runtime',
                region_name=region,
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key
            )
            print("✅ Bedrockクライアント初期化完了 (Access Keys)")
    except Exception as e:
        print(f"❌ クライアント初期化エラー: {e}")
        return False
    
    # Test API call
    print("\n" + "-"*70)
    print("テストプロンプトを送信中...")
    print("-"*70 + "\n")
    
    test_prompt = """以下の3つの意見を要約してください:

1. このサービスは使いやすくて良いと思います
2. もう少し機能が増えると嬉しいです
3. デザインがシンプルで分かりやすい

簡潔に要約してください。"""
    
    try:
        # Build request body
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 200,
            "temperature": 0.7,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": test_prompt
                        }
                    ]
                }
            ]
        }
        
        # Call Bedrock API
        if use_bearer:
            # Use Bearer token with requests
            import requests
            
            endpoint = f"https://bedrock-runtime.{region}.amazonaws.com/model/{model_id}/invoke"
            headers = {
                'Authorization': f'Bearer {bearer_token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            response = requests.post(
                endpoint,
                headers=headers,
                json=body,
                timeout=30
            )
            response.raise_for_status()
            response_body = response.json()
        else:
            # Use boto3 client
            response = client.invoke_model(
                modelId=model_id,
                contentType='application/json',
                accept='application/json',
                body=json.dumps(body)
            )
            response_body = json.loads(response['body'].read())
        
        # Extract content
        content = ''
        if 'content' in response_body and isinstance(response_body['content'], list):
            for item in response_body['content']:
                if item.get('type') == 'text':
                    content += item.get('text', '')
        
        print("📝 生成されたレスポンス:")
        print("-"*70)
        print(content)
        print("-"*70)
        
        # Token usage
        if 'usage' in response_body:
            print(f"\n📊 使用トークン数:")
            print(f"   入力: {response_body['usage'].get('input_tokens', 0)}")
            print(f"   出力: {response_body['usage'].get('output_tokens', 0)}")
            print(f"   合計: {response_body['usage'].get('input_tokens', 0) + response_body['usage'].get('output_tokens', 0)}")
        
        print("\n✅ Bedrock API接続テスト成功!")
        print("="*70 + "\n")
        
        return True
        
    except Exception as e:
        print(f"❌ API呼び出しエラー: {e}")
        print("\n考えられる原因:")
        print("1. AWS認証情報が無効または期限切れ")
        print("2. Bedrockのモデルアクセスが有効化されていない")
        print("   → AWS Console > Bedrock > Model access で確認")
        print("3. IAMユーザー/トークンにbedrock:InvokeModel権限がない")
        print("4. モデルIDが正しくない")
        print("5. 選択したリージョンでBedrockが利用できない")
        if use_bearer:
            print("6. Bearer Tokenを使用する場合はInference Profile IDが必要")
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
        import boto3
        print(f"  ✅ boto3: {boto3.__version__}")
    except ImportError:
        print("  ❌ boto3: インストールされていません")
    
    try:
        from dotenv import load_dotenv
        print("  ✅ python-dotenv: インストール済み")
    except ImportError:
        print("  ❌ python-dotenv: インストールされていません")
    
    try:
        import requests
        print(f"  ✅ requests: {requests.__version__}")
    except ImportError:
        print("  ❌ requests: インストールされていません")
    
    # Check .env file
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        print(f"\n✅ .envファイル: 存在します ({env_file})")
    else:
        print(f"\n⚠️  .envファイル: 存在しません ({env_file})")
        print("   env_bedrock_sample.txtをコピーして.envを作成してください:")
        print("   cp env_bedrock_sample.txt .env")
    
    print("-"*70 + "\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test Amazon Bedrock API connection",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--model',
        choices=list(BEDROCK_MODELS.keys()),
        default='sonnet-4.5-eu',
        help='Model to test (default: sonnet-4.5-eu)'
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
    
    # Test connection
    success = test_bedrock_connection(args.model)
    
    if success:
        print("\n🎉 すべてのテストに合格しました!")
        print("summarize_surveys_bedrock.pyを実行する準備が整いました。")
        return 0
    else:
        print("\n❌ テストが失敗しました")
        print("上記のエラーメッセージを確認して問題を解決してください。")
        return 1


if __name__ == "__main__":
    exit(main())









