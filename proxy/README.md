# MCP Proxy Server with Bearer Token Authentication

シンプルなプロキシサーバーで、受信したリクエストにBearerトークンを追加してDataRobotのMCPサーバーに転送します。

## 特徴

- **認証なし**: プロキシ自体は認証不要（ChatGPTから直接アクセス可能）
- **Bearer認証追加**: DataRobotへのリクエストにBearerトークンを自動追加
- **シンプル**: 最小限の依存関係とコード

## セットアップ

### 1. 依存関係のインストール

```bash
cd proxy
pip install -r requirements.txt
```

### 2. 環境変数の設定

`.env`ファイルを作成：

```bash
cp .env.example .env
```

`.env`を編集：

```env
MCP_SERVER_URL=https://app.jp.datarobot.com/custom_applications/YOUR_APP_ID
BEARER_TOKEN=your-datarobot-bearer-token
```

### 3. プロキシサーバーの起動

```bash
python proxy_server.py --host 0.0.0.0 --port 8000
```

## 使用方法

### ChatGPTから接続

ChatGPTのMCP設定で以下のURLを指定：

```
http://your-azure-server:8000/mcp
```

プロキシが自動的にBearerトークンを追加してDataRobotに転送します。

### ローカルテスト

```bash
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"initialize","id":1}'
```

## Azureへのデプロイ

### Azure Container Instances (推奨)

```bash
# Dockerイメージのビルド
docker build -t mcp-proxy:latest -f Dockerfile .

# Azure Container Registryにプッシュ
az acr login --name yourregistry
docker tag mcp-proxy:latest yourregistry.azurecr.io/mcp-proxy:latest
docker push yourregistry.azurecr.io/mcp-proxy:latest

# Container Instanceの作成
az container create \
  --resource-group your-resource-group \
  --name mcp-proxy \
  --image yourregistry.azurecr.io/mcp-proxy:latest \
  --dns-name-label mcp-proxy-unique \
  --ports 8000 \
  --environment-variables \
    MCP_SERVER_URL='https://app.jp.datarobot.com/custom_applications/YOUR_APP_ID' \
    BEARER_TOKEN='your-bearer-token'
```

### Azure App Service

```bash
# App Serviceの作成
az webapp create \
  --resource-group your-resource-group \
  --plan your-app-service-plan \
  --name mcp-proxy \
  --runtime "PYTHON:3.11"

# 環境変数の設定
az webapp config appsettings set \
  --resource-group your-resource-group \
  --name mcp-proxy \
  --settings \
    MCP_SERVER_URL='https://app.jp.datarobot.com/custom_applications/YOUR_APP_ID' \
    BEARER_TOKEN='your-bearer-token'

# コードのデプロイ
az webapp up --name mcp-proxy
```

## エンドポイント

| エンドポイント | 説明 |
|---------------|------|
| `/health` | ヘルスチェック |
| `/mcp` | MCPエンドポイント（JSON-RPC） |
| その他全て | DataRobotに転送 |

## セキュリティ考慮事項

⚠️ **注意**: このプロキシは認証なしで動作します。本番環境では以下の対策を推奨：

1. **Azure Network Security Group**: IPアドレス制限
2. **Azure Private Endpoint**: プライベートネットワーク内に配置
3. **Azure Front Door**: WAFでDDoS対策
4. **API Key認証**: 最小限の認証を追加

## トラブルシューティング

### プロキシが起動しない

```bash
# ログを確認
python proxy_server.py --host 0.0.0.0 --port 8000
```

### 環境変数が読み込まれない

`.env`ファイルがproxy/ディレクトリにあることを確認。

### DataRobotに接続できない

`MCP_SERVER_URL`が正しいか確認。DataRobotのアプリケーションURLを使用。

## ライセンス

このプロキシサーバーはMIT Licenseで提供されています。
