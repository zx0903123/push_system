"""
通知歷史記錄模組
負責記錄和管理所有通知的發送歷史
"""
from pydantic import BaseModel
from typing import Optional, List
import datetime


class NotificationHistory(BaseModel):
    """通知歷史記錄模型"""
    id: Optional[int] = None
    log_id: Optional[int] = None  # 關聯的日誌 ID
    channel: str  # 通知渠道
    recipient: str  # 接收者（Email、電話號碼等）
    title: str  # 通知標題
    message: str  # 通知內容
    status: str  # 發送狀態
    error_message: Optional[str] = None  # 錯誤訊息
    retry_count: int = 0  # 重試次數
    sent_at: Optional[datetime.datetime] = None  # 發送時間
    created_at: datetime.datetime = None  # 建立時間
    
    class Config:
        json_encoders = {
            datetime.datetime: lambda v: v.isoformat() if v else None
        }
        
    def __init__(self, **data):
        if 'created_at' not in data or data['created_at'] is None:
            data['created_at'] = datetime.datetime.now()
        super().__init__(**data)
