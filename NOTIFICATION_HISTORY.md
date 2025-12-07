# 通知歷史記錄功能說明

## 📋 功能概述

通知歷史記錄系統會自動記錄每一次通知發送的詳細資訊，包括：
- 通知渠道（Email、Line、Teams、Slack、Discord、SMS）
- 接收者資訊
- 發送狀態（成功/失敗）
- 錯誤訊息（如果失敗）
- 重試次數
- 發送時間

## 🎯 主要功能

### 1. 自動記錄
每次發送通知時，系統會自動記錄到資料庫：
```python
# 在 message.py 中的每個發送函數都會調用
_save_notification_history(
    log_id=log_id,              # 關聯的日誌 ID
    channel="email",            # 通知渠道
    recipient="user@email.com", # 接收者
    title="系統通知",           # 標題
    message="通知內容",         # 訊息
    status="success",           # 狀態
    retry_count=0               # 重試次數
)
```

### 2. 查詢通知歷史 API

#### GET /notifications/history
查詢通知歷史列表，支援多條件篩選和分頁。

**請求參數：**
- `log_id` (可選): 篩選特定日誌的通知
- `channel` (可選): 篩選通知渠道 (email/line/teams/slack/discord/sms)
- `status` (可選): 篩選狀態 (success/failed/pending/retrying)
- `date_from` (可選): 開始日期
- `date_to` (可選): 結束日期
- `limit` (預設 50): 每頁筆數
- `offset` (預設 0): 偏移量

**使用範例：**
```bash
# 查詢所有通知歷史
GET /notifications/history

# 查詢特定日誌的通知
GET /notifications/history?log_id=123

# 查詢失敗的 Email 通知
GET /notifications/history?channel=email&status=failed

# 查詢特定日期範圍
GET /notifications/history?date_from=2024-12-01&date_to=2024-12-07&limit=100
```

**回應格式：**
```json
{
  "status": "success",
  "data": [
    {
      "id": 1,
      "log_id": 123,
      "channel": "email",
      "recipient": "user@example.com",
      "title": "系統通知",
      "message": "通知內容",
      "status": "success",
      "error_message": null,
      "retry_count": 0,
      "sent_at": "2024-12-07T14:30:00",
    }
  ],
  "count": 1,
  "limit": 50,
  "offset": 0
}
```

#### GET /notifications/history/{notification_id}
查詢單筆通知歷史的詳細資訊。

**使用範例：**
```bash
GET /notifications/history/123
```

**回應格式：**
```json
{
  "status": "success",
  "data": {
    "id": 123,
    "log_id": 456,
    "channel": "line",
    "recipient": "Line Notify",
    "title": "Line 通知",
    "message": "系統發生錯誤",
    "status": "success",
    "error_message": null,
    "retry_count": 1,
    "sent_at": "2024-12-07T14:30:00",
  }
}
```

#### GET /notifications/statistics
查詢通知統計資訊。

**請求參數：**
- `date_from` (可選): 開始日期（預設 7 天前）
- `date_to` (可選): 結束日期（預設今天）

**使用範例：**
```bash
# 查詢最近 7 天（預設）
GET /notifications/statistics

# 查詢指定日期範圍
GET /notifications/statistics?date_from=2024-12-01&date_to=2024-12-07
```

**回應格式：**
```json
{
  "status": "success",
  "period": {
    "from": "2024-12-01",
    "to": "2024-12-07"
  },
  "total_notifications": 150,
  "by_channel": {
    "email": 80,
    "line": 30,
    "teams": 20,
    "slack": 15,
    "sms": 5
  },
  "by_status": {
    "success": 135,
    "failed": 15
  },
  "success_rate": 90.0,
  "success_count": 135,
  "failed_count": 15
}
```

## 📊 資料庫結構

需要建立 `TB_NOTIFICATION_HISTORY` 資料表：

```sql
CREATE TABLE TB_NOTIFICATION_HISTORY (
    id SERIAL PRIMARY KEY,
    log_id INTEGER REFERENCES TB_LOGS(id),
    recipient VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    status VARCHAR(20) NOT NULL,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    sent_at TIMESTAMP,
);

-- 建立索引提升查詢效能
CREATE INDEX idx_notification_log_id ON TB_NOTIFICATION_HISTORY(log_id);
CREATE INDEX idx_notification_status ON TB_NOTIFICATION_HISTORY(status);
```

## 🔍 使用場景

### 1. 追蹤通知發送狀況
查看特定日誌觸發了哪些通知，誰收到了通知：
```bash
GET /notifications/history?log_id=123
```

### 2. 監控失敗通知
查找失敗的通知並分析原因：
```bash
GET /notifications/history?status=failed&limit=100
```

### 3. 通知效能分析
查看各渠道的成功率和發送量：
```bash
GET /notifications/statistics?date_from=2024-12-01&date_to=2024-12-07
```

### 4. 審計追蹤
追蹤誰在什麼時候收到了什麼通知：
```bash
GET /notifications/history?date_from=2024-12-07&date_to=2024-12-07
```

## ✨ 特色功能

### 1. 自動關聯日誌
每筆通知記錄都會關聯到觸發它的日誌 ID，方便追蹤。

### 2. 詳細的錯誤資訊
失敗的通知會記錄詳細的錯誤訊息，便於排查問題。

### 3. 重試計數
記錄每次通知嘗試的次數，了解哪些通知需要多次重試。

### 4. 時間戳記
記錄通知建立時間和成功發送時間，便於分析發送延遲。

### 5. 多渠道支援
支援所有通知渠道的歷史記錄（Email、Line、Teams、Slack、Discord、SMS）。

## 🚀 未來擴展

可以基於通知歷史實作更多功能：
- 重發失敗的通知
- 通知模板管理
- 接收者訂閱管理
- 通知優先級管理
- 通知排程發送
- 通知群組管理

## 📝 注意事項

1. 通知歷史會持續累積，建議定期清理舊資料
2. 敏感資訊（如手機號碼）會被記錄，需注意資料安全
3. 大量通知可能會影響資料庫效能，建議使用索引優化
4. 失敗通知的錯誤訊息可能包含敏感資訊，需控制訪問權限
