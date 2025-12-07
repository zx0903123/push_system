# Push System - 系統日誌與推播通知系統

這是一個基於 FastAPI 的系統日誌記錄與自動通知推播系統，支援多種通知渠道。

## 🎯 系統功能

### 核心功能
- 📝 **日誌記錄** - 接收並記錄系統日誌，自動判斷重複問題
- 🔔 **智能通知** - 根據風險等級和發生次數自動發送通知
- 📊 **統計分析** - 提供日誌和通知的統計分析
- 📜 **歷史查詢** - 查詢日誌和通知發送歷史
- 🔄 **自動重試** - 失敗的通知自動重試，並記錄詳細歷史

### 支援的通知渠道
- 📧 Email (Gmail)
- 💬 Line Notify
- 💼 Microsoft Teams
- 💬 Slack
- 🎮 Discord
- 📱 SMS (透過 Email to SMS Gateway)

## 📋 環境設定

### 1. 環境變數配置

複製範例環境檔並填入實際的設定值：

```powershell
# 複製環境變數範本
cp .env.example .env
```

編輯 `.env` 檔案並更新以下必要變數：

**資料庫設定：**
- `SUPABASE_URL` - 你的 Supabase 專案 URL
- `SUPABASE_KEY` - 你的 Supabase anon/public key
- `REDIS_HOST` - Redis 主機位址
- `REDIS_PORT` - Redis 埠號（預設 6379）
- `REDIS_PASSWORD` - Redis 密碼

**Email 設定：**
- `SENDER_EMAIL` - 發送通知的 Email 地址
- `APP_PASSWORD` - Email 應用程式密碼（Gmail 需使用應用程式密碼）

**通知渠道設定（選填）：**
- `LINE_TOKEN` - Line Notify 的 Token
- `TEAMS_URL` - Microsoft Teams Webhook URL
- `SLACK_URL` - Slack Webhook URL
- `DISCORD_URL` - Discord Webhook URL
- `EMAIL_TO_SMS_GATEWAY` - SMS Gateway 網域（如 vtext.com）

### 2. 安裝相依套件

建立虛擬環境並安裝套件：

```powershell
# 建立虛擬環境
python -m venv .venv

# 啟動虛擬環境
.\.venv\Scripts\Activate.ps1

# 安裝相依套件
pip install -r requirements.txt
```

### 3. 本地執行

使用 PowerShell 執行開發伺服器：

```powershell
# 啟動 FastAPI 開發伺服器（支援熱重載）
uvicorn app.main:app --reload
```

執行測試：

```powershell
# 執行單元測試
pytest -q
```

API 文件將會在以下網址提供：
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### 4. 使用 Docker 執行

使用 Docker Compose 建置並啟動容器：

```powershell
# 切換到專案目錄
cd 'C:\Users\homet\OneDrive\桌面\Programing\SideProject\push_system'

# 建置並啟動容器
docker-compose up --build
```

容器啟動後，可以使用 Postman 匯入 `postman_collection_push_system.json` 來測試 API。

## 📡 API 端點

### 系統狀態
- `GET /` - API 根路徑，回傳系統資訊
- `GET /health` - 健康檢查端點

### 日誌管理
- `GET /logs` - 接收並記錄系統日誌（自動通知）
- `GET /logs/list` - 查詢日誌列表（支援分頁和篩選）
- `GET /logs/{log_id}` - 查詢單筆日誌詳情
- `GET /logs/statistics` - 查詢日誌統計資訊

### 通知歷史
- `GET /notifications/history` - 查詢通知發送歷史（支援篩選）
- `GET /notifications/history/{notification_id}` - 查詢單筆通知詳情
- `GET /notifications/statistics` - 查詢通知統計資訊

## 🔐 安全性注意事項

⚠️ **重要：絕對不要將 `.env` 檔案提交到版本控制系統！**

`.env` 檔案包含敏感的憑證資訊，例如：
- 資料庫連線資訊
- API 金鑰
- Email 密碼
- Webhook URL

確保 `.gitignore` 檔案中包含 `.env` 以防止意外提交。

## 📊 資料庫結構

系統需要以下資料表（在 Supabase 中建立）：

```sql
-- 日誌記錄表
CREATE TABLE TB_LOGS (
    id SERIAL PRIMARY KEY,
    riskLevel INTEGER NOT NULL,
    type INTEGER NOT NULL,
    location VARCHAR(255) NOT NULL,
    function VARCHAR(255) NOT NULL,
    log TEXT NOT NULL,
    employees TEXT[],
    date DATE NOT NULL,
    time TIME NOT NULL,
    count INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 通知歷史表
CREATE TABLE TB_NOTIFICATION_HISTORY (
    id SERIAL PRIMARY KEY,
    log_id INTEGER REFERENCES TB_LOGS(id),
    channel VARCHAR(20) NOT NULL,
    recipient VARCHAR(255) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    status VARCHAR(20) NOT NULL,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    sent_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 員工聯絡資訊表
CREATE TABLE TB_EMPLOYEE_CONTACT (
    id SERIAL PRIMARY KEY,
    no VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    contactWay INTEGER NOT NULL,
    email VARCHAR(255),
    line VARCHAR(255),
    teams VARCHAR(255),
    slack VARCHAR(255),
    discord VARCHAR(255),
    phone VARCHAR(50)
);
```

## 🚀 使用範例

### 記錄日誌並觸發通知

```bash
GET http://localhost:8000/logs?riskLevel=2&location=API&function=UserService&log=連線失敗&employees=emp001,emp002
```

### 查詢日誌列表

```bash
GET http://localhost:8000/logs/list?riskLevel=2&limit=20
```

### 查詢通知歷史

```bash
GET http://localhost:8000/notifications/history?status=failed
```

### 查詢統計資訊

```bash
GET http://localhost:8000/logs/statistics?date_from=2024-12-01&date_to=2024-12-07
```

## 📚 相關文件

- `NOTIFICATION_HISTORY.md` - 通知歷史記錄功能詳細說明
- `.env.example` - 環境變數範本

## 🛠️ 技術堆疊

- **框架**: FastAPI
- **資料庫**: Supabase (PostgreSQL)
- **快取**: Redis
- **通知**: SMTP, Webhooks, Line Notify
- **測試**: Pytest
- **容器化**: Docker, Docker Compose

## 📝 開發說明

### 風險等級定義
- `0` - 無風險
- `1` - 普通（累積 5 次發送通知）
- `2` - 高風險（累積 3 次發送通知）
- `3` - 緊急（立即發送通知）

### 通知邏輯
1. 系統收到日誌記錄請求
2. 檢查是否為重複問題（相同 location + function + log）
3. 如果是重複問題，增加計數；否則新建記錄
4. 根據風險等級和計數判斷是否需要發送通知
5. 發送通知到所有配置的渠道
6. 記錄通知發送歷史（成功或失敗）

## 🤝 貢獻

歡迎提交 Issue 和 Pull Request！

## 📄 授權

本專案採用 MIT 授權條款。

AI推薦的實作功能
日誌查詢 API (V)
通知歷史記錄 (V)
員工管理 API
通知規則配置
批次操作
儀表板數據 API
通知測試功能
Webhook 回調
日誌搜尋
身份驗證與授權
智能分析
排程任務
Redis 快取優化
