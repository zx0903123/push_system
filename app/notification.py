"""
通知歷史記錄模組
負責記錄和管理所有通知的發送歷史
"""
from pydantic import BaseModel
from typing import Optional
import logging
from datetime import datetime
import app.database as db
from app.object import DBFilter
from app.constants import Channel, Status


logger = logging.getLogger(__name__)


class NotificationHistory(BaseModel):
    """通知歷史記錄模型"""
    id: Optional[int] = None
    log_id: Optional[int] = None  # 關聯的日誌 ID
    recipient: str  # 接收者（Email、電話號碼等）
    message: str  # 通知內容
    status: int  # 發送狀態
    error_message: Optional[str] = None  # 錯誤訊息
    retry_count: int = 0  # 重試次數
    sent_at: Optional[str] = None  # 發送時間（ISO 格式字串）


# 保存通知歷史記錄的輔助函數
def _save_notification_history(notic_history: NotificationHistory) -> bool:
    """
    保存通知歷史記錄到資料庫。
    如果已存在相同的記錄（log_id、recipient、message 相同），則更新 retry_count。
    返回 True 表示保存成功，False 表示保存失敗（但不影響主流程）
    """
    if notic_history.log_id is None:
        logger.warning("log_id 為 None，無法保存通知歷史")
        return False
    
    try:
        notic_history.sent_at = datetime.now().isoformat()
        
        # 檢查是否已存在相同的記錄（log_id + recipient + message 三者組合）
        existing = db.supabase.table("TB_NOTIFICATION_HISTORY").select("*").eq(
            "log_id", notic_history.log_id
        ).eq(
            "recipient", notic_history.recipient
        ).eq(
            "message", notic_history.message
        ).execute()
        
        if existing.data and len(existing.data) > 0:
            # 找到重複記錄，更新 retry_count 和其他欄位
            existing_record = existing.data[0]
            new_retry_count = existing_record.get('retry_count', 0) + 1
            
            # 準備更新資料
            update_data = {
                'retry_count': new_retry_count,
                'status': notic_history.status,
                'error_message': notic_history.error_message,
                'sent_at': notic_history.sent_at
            }
            
            # 使用 db.update() 更新記錄
            result = db.update(
                "TB_NOTIFICATION_HISTORY", 
                {**existing_record, **update_data},
                [DBFilter(name="id", operator=db.Opreator.EQUAL.value, values=[str(existing_record['id'])])]
            )
            
            if result:
                logger.info(f"通知歷史記錄已更新: ID={existing_record['id']}, retry_count={new_retry_count}")
                return True
            else:
                logger.error("更新通知歷史記錄失敗")
                return False
        else:
            # 不存在重複記錄，新增
            history_data = notic_history.model_dump(exclude={'id'})
            db.supabase.table("TB_NOTIFICATION_HISTORY").insert(history_data).execute()
            logger.info(f"通知歷史記錄已保存: {notic_history.message} - {notic_history.status} - 收件者: {notic_history.recipient}")
            return True
            
    except Exception as e:
        logger.error(f"保存通知歷史記錄失敗: {e}", exc_info=True)
        # 保存歷史失敗不應該影響主流程，只記錄錯誤
        return False
