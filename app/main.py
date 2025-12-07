import datetime
from fastapi import FastAPI, Query, HTTPException, Path
from typing import List, Dict, Any, Optional
import app.database as db
from app.object import Log
from app.notification import NotificationHistory, NotificationStatus, NotificationChannel
import logging

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Push System API",
    description="系統日誌記錄與通知推播系統",
    version="1.0.0"
)


@app.get("/", response_model=Dict[str, str])
def root() -> Dict[str, str]:
    """API 根路徑"""
    return {
        "message": "Push System API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health", response_model=Dict[str, str])
def health_check() -> Dict[str, str]:
    """健康檢查 endpoint"""
    return {"status": "healthy", "service": "push_system"}


@app.get("/logs", response_model=Dict[str, Any])
def logs(
        riskLevel: int = Query(0, ge=0, le=3, description="風險等級: 0=無, 1=普通, 2=高風險, 3=緊急"),
        type: int = Query(0, ge=0, description="日誌類型"),
        location: str = Query("", description="發生位置"),
        function: str = Query("", description="功能模組"),
        log: str = Query("", description="日誌內容"),
        employees: List[str] = Query([], description="相關員工列表"),
        date: datetime.date = Query(default_factory=lambda: datetime.datetime.now().date()),
        time: datetime.time = Query(default_factory=lambda: datetime.datetime.now().time())
    ) -> Dict[str, Any]:
    """接收並記錄系統日誌，自動判斷是否需要通知相關人員"""
    try:
        # 驗證必要欄位
        if not location or not function or not log:
            raise HTTPException(
                status_code=400, 
                detail="location, function, log 為必填欄位"
            )
        
        # 接收log資料
        item = Log(
            riskLevel=riskLevel,
            type=type,
            location=location,
            function=function,
            log=log,
            employees=employees,
            date=date,
            time=time
        )

        # 判斷是否為重複問題的Log 是就增加次數 否則新增一筆
        if db.check_log(item):
            item.count += 1
            result = db.update_log(item)
            if result is None:
                raise HTTPException(status_code=500, detail="更新日誌失敗")
            logger.info(f"日誌已更新: {location}/{function} - 次數: {item.count}")
            return {"status": "updated", "message": "日誌次數已更新", "count": item.count}
        else:
            result = db.insert_log(item)
            if result is None:
                raise HTTPException(status_code=500, detail="新增日誌失敗")
            logger.info(f"新增日誌: {location}/{function}")
            return {"status": "created", "message": "日誌已建立"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"處理日誌時發生錯誤: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"處理日誌失敗: {str(e)}")


@app.get("/logs/list", response_model=Dict[str, Any])
def get_logs_list(
        riskLevel: int = Query(None, ge=0, le=3, description="篩選風險等級"),
        location: str = Query(None, description="篩選位置"),
        function: str = Query(None, description="篩選功能模組"),
        date_from: datetime.date = Query(None, description="開始日期"),
        date_to: datetime.date = Query(None, description="結束日期"),
        limit: int = Query(10, ge=1, le=100, description="每頁筆數"),
        offset: int = Query(0, ge=0, description="偏移量")
    ) -> Dict[str, Any]:
    """查詢日誌列表，支援分頁和篩選"""
    try:
        filters = []
        
        # 根據參數建立篩選條件
        if riskLevel is not None:
            filters.append(db.DBFilter(name="riskLevel", operator=db.Opreator.EQUAL, values=[str(riskLevel)]))
        if location:
            filters.append(db.DBFilter(name="location", operator=db.Opreator.ILIKE, values=[f"%{location}%"]))
        if function:
            filters.append(db.DBFilter(name="function", operator=db.Opreator.ILIKE, values=[f"%{function}%"]))
        if date_from:
            filters.append(db.DBFilter(name="date", operator=db.Opreator.GREATER_OR_EQUAL, values=[str(date_from)]))
        if date_to:
            filters.append(db.DBFilter(name="date", operator=db.Opreator.LESS_OR_EQUAL, values=[str(date_to)]))
        
        # 查詢資料
        result = db.get_logs_with_pagination(filters, limit, offset)
        
        if result is None:
            raise HTTPException(status_code=500, detail="查詢日誌失敗")
        
        return {
            "status": "success",
            "data": result.data if result.data else [],
            "count": len(result.data) if result.data else 0,
            "limit": limit,
            "offset": offset
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查詢日誌列表時發生錯誤: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查詢失敗: {str(e)}")


@app.get("/logs/{log_id}", response_model=Dict[str, Any])
def get_log_by_id(log_id: int) -> Dict[str, Any]:
    """根據 ID 查詢單筆日誌詳情"""
    try:
        filters = [db.DBFilter(name="id", operator=db.Opreator.EQUAL, values=[str(log_id)])]
        result = db.call_by_filters("TB_LOGS", filters)
        
        if result is None or not result.data or len(result.data) == 0:
            raise HTTPException(status_code=404, detail=f"找不到 ID 為 {log_id} 的日誌")
        
        return {
            "status": "success",
            "data": result.data[0]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查詢日誌詳情時發生錯誤: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查詢失敗: {str(e)}")


# 查詢最近 7 天（預設）
# 指定日期範圍
@app.get("/logs/statistics", response_model=Dict[str, Any])
def get_logs_statistics(
        date_from: datetime.date = Query(None, description="開始日期"),
        date_to: datetime.date = Query(None, description="結束日期")
    ) -> Dict[str, Any]:
    """查詢日誌統計資訊（按風險等級、位置統計）"""
    try:
        # 如果沒有指定日期，預設查詢最近 7 天
        if not date_from:
            date_from = datetime.date.today() - datetime.timedelta(days=7)
        if not date_to:
            date_to = datetime.date.today()
        
        filters = [
            db.DBFilter(name="date", operator=db.Opreator.GREATER_OR_EQUAL, values=[str(date_from)]),
            db.DBFilter(name="date", operator=db.Opreator.LESS_OR_EQUAL, values=[str(date_to)])
        ]
        
        result = db.call_by_filters("TB_LOGS", filters)
        
        if result is None or not result.data:
            return {
                "status": "success",
                "period": {"from": str(date_from), "to": str(date_to)},
                "total_logs": 0,
                "by_risk_level": {},
                "by_location": {},
                "by_function": {}
            }
        
        logs = result.data
        
        # 統計資料
        by_risk_level = {}
        by_location = {}
        by_function = {}
        
        for log_item in logs:
            risk = log_item.get('riskLevel', 0)
            location = log_item.get('location', 'Unknown')
            function = log_item.get('function', 'Unknown')
            
            # 按風險等級統計
            by_risk_level[risk] = by_risk_level.get(risk, 0) + 1
            
            # 按位置統計
            by_location[location] = by_location.get(location, 0) + 1
            
            # 按功能統計
            by_function[function] = by_function.get(function, 0) + 1
        
        return {
            "status": "success",
            "period": {"from": str(date_from), "to": str(date_to)},
            "total_logs": len(logs),
            "by_risk_level": by_risk_level,
            "by_location": dict(sorted(by_location.items(), key=lambda x: x[1], reverse=True)[:10]),
            "by_function": dict(sorted(by_function.items(), key=lambda x: x[1], reverse=True)[:10])
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查詢統計資訊時發生錯誤: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查詢統計失敗: {str(e)}")


# ==================== 通知歷史 API ====================

@app.get("/notifications/history", response_model=Dict[str, Any])
def get_notification_history(
        log_id: Optional[int] = Query(None, description="篩選特定日誌的通知"),
        channel: Optional[str] = Query(None, description="篩選通知渠道"),
        status: Optional[str] = Query(None, description="篩選通知狀態"),
        date_from: datetime.date = Query(None, description="開始日期"),
        date_to: datetime.date = Query(None, description="結束日期"),
        limit: int = Query(50, ge=1, le=500, description="每頁筆數"),
        offset: int = Query(0, ge=0, description="偏移量")
    ) -> Dict[str, Any]:
    """查詢通知歷史記錄"""
    try:
        filters = []
        
        if log_id is not None:
            filters.append(db.DBFilter(name="log_id", operator=db.Opreator.EQUAL, values=[str(log_id)]))
        if channel:
            filters.append(db.DBFilter(name="channel", operator=db.Opreator.EQUAL, values=[channel]))
        if status:
            filters.append(db.DBFilter(name="status", operator=db.Opreator.EQUAL, values=[status]))
        if date_from:
            filters.append(db.DBFilter(name="created_at", operator=db.Opreator.GREATER_OR_EQUAL, values=[str(date_from)]))
        if date_to:
            filters.append(db.DBFilter(name="created_at", operator=db.Opreator.LESS_OR_EQUAL, values=[str(date_to)]))
        
        # 查詢通知歷史
        query = db.supabase.table("TB_NOTIFICATION_HISTORY").select("*")
        for f in filters:
            query = query.filter(f.name, f.operator, f.values[0] if len(f.values) == 1 else f.values)
        
        query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
        result = query.execute()
        
        return {
            "status": "success",
            "data": result.data if result.data else [],
            "count": len(result.data) if result.data else 0,
            "limit": limit,
            "offset": offset
        }
    
    except Exception as e:
        logger.error(f"查詢通知歷史時發生錯誤: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查詢失敗: {str(e)}")


@app.get("/notifications/history/{notification_id}", response_model=Dict[str, Any])
def get_notification_by_id(notification_id: int = Path(..., description="通知歷史 ID")) -> Dict[str, Any]:
    """查詢單筆通知歷史詳情"""
    try:
        filters = [db.DBFilter(name="id", operator=db.Opreator.EQUAL, values=[str(notification_id)])]
        result = db.call_by_filters("TB_NOTIFICATION_HISTORY", filters)
        
        if result is None or not result.data or len(result.data) == 0:
            raise HTTPException(status_code=404, detail=f"找不到 ID 為 {notification_id} 的通知記錄")
        
        return {
            "status": "success",
            "data": result.data[0]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查詢通知詳情時發生錯誤: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查詢失敗: {str(e)}")


@app.get("/notifications/statistics", response_model=Dict[str, Any])
def get_notification_statistics(
        date_from: datetime.date = Query(None, description="開始日期"),
        date_to: datetime.date = Query(None, description="結束日期")
    ) -> Dict[str, Any]:
    """查詢通知統計資訊"""
    try:
        # 預設查詢最近 7 天
        if not date_from:
            date_from = datetime.date.today() - datetime.timedelta(days=7)
        if not date_to:
            date_to = datetime.date.today()
        
        filters = [
            db.DBFilter(name="created_at", operator=db.Opreator.GREATER_OR_EQUAL, values=[str(date_from)]),
            db.DBFilter(name="created_at", operator=db.Opreator.LESS_OR_EQUAL, values=[str(date_to)])
        ]
        
        result = db.call_by_filters("TB_NOTIFICATION_HISTORY", filters)
        
        if result is None or not result.data:
            return {
                "status": "success",
                "period": {"from": str(date_from), "to": str(date_to)},
                "total_notifications": 0,
                "by_channel": {},
                "by_status": {},
                "success_rate": 0.0
            }
        
        notifications = result.data
        
        # 統計資料
        by_channel = {}
        by_status = {}
        success_count = 0
        
        for notif in notifications:
            channel = notif.get('channel', 'Unknown')
            status = notif.get('status', 'Unknown')
            
            by_channel[channel] = by_channel.get(channel, 0) + 1
            by_status[status] = by_status.get(status, 0) + 1
            
            if status == NotificationStatus.SUCCESS:
                success_count += 1
        
        total = len(notifications)
        success_rate = (success_count / total * 100) if total > 0 else 0.0
        
        return {
            "status": "success",
            "period": {"from": str(date_from), "to": str(date_to)},
            "total_notifications": total,
            "by_channel": by_channel,
            "by_status": by_status,
            "success_rate": round(success_rate, 2),
            "success_count": success_count,
            "failed_count": total - success_count
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查詢通知統計時發生錯誤: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查詢統計失敗: {str(e)}")