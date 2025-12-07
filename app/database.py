import app.message as msg
import redis
from supabase import create_client, Client
from app.settings import settings
from app.object import DBFilter, Log, Message
from typing import Optional, List, Any
import logging
from enum import Enum

logger = logging.getLogger(__name__)


# 運算子常數
class Opreator(str, Enum):
    EQUAL = "eq" # 等於
    NOEQUAL = "neq" # 不等於
    GREATER = "gt" # 大於
    GREATER_OR_EQUAL = "gte" # 大於等於
    LESS = "lt" # 小於
    LESS_OR_EQUAL = "lte" # 小於等於
    LIKE = "like" # 區分大小寫
    ILIKE = "ilike" # 不區分大小寫
    IS = "is_" # 等同Equal但可以用於Null值
    NO_IS = "not_is_" # 等同NoEqual但可以用於Null值
    IN = "in_" # 包含於列表中
    OR = "or" # 或條件


# 使用環境變數建立 Redis 連線
r = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    decode_responses=True,
    username=settings.REDIS_USERNAME,
    password=settings.REDIS_PASSWORD,
)

# 使用環境變數建立 Supabase 連線
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


# 建立Filter用來查詢特定資料
def makeFilter(query, filters: list[DBFilter]):
    for f in filters:
        # 使用 DBFilter 的屬性，而不是解包元組
        # 如果 values 只有一個元素，直接使用該值；否則使用整個列表
        value = f.values[0] if len(f.values) == 1 else f.values
        query = query.filter(f.name, f.operator, value)
    return query


# 新增資料
def insert(table_name: str, data: dict) -> Optional[Any]:
    try:
        result = supabase.table(table_name).insert(data).execute()
        return result
    except Exception as e:
        logger.error(f"插入資料到 {table_name} 時發生錯誤: {e}", exc_info=True)
        return None


# 更新資料
def update(table_name: str, data: dict, filters: List[DBFilter]) -> Optional[Any]:
    try:
        query = supabase.table(table_name).update(data)
        result = makeFilter(query, filters).execute()
        return result
    except Exception as e:
        logger.error(f"更新 {table_name} 資料時發生錯誤: {e}", exc_info=True)
        return None


# 插入或更新資料
def upsert(table_name: str, data: dict, filters: List[DBFilter]) -> Optional[Any]:
    try:
        query = supabase.table(table_name).upsert(data)
        result = makeFilter(query, filters).execute()
        return result
    except Exception as e:
        logger.error(f"Upsert {table_name} 資料時發生錯誤: {e}", exc_info=True)
        return None


# 刪除資料
def delete(table_name: str, filters: List[DBFilter]) -> Optional[Any]:
    try:
        query = supabase.table(table_name).delete()
        result = makeFilter(query, filters).execute()
        return result
    except Exception as e:
        logger.error(f"刪除 {table_name} 資料時發生錯誤: {e}", exc_info=True)
        return None


# 用SQL查詢資料庫
def call_by_sql(table_name: str, sql: dict) -> Optional[Any]:
    try:
        result = supabase.rpc(sql).execute()
        return result
    except Exception as e:
        logger.error(f"執行 SQL 查詢 {table_name} 時發生錯誤: {e}", exc_info=True)
        return None


# 用物件查詢資料庫
def call_by_filters(table_name: str, filters: List[DBFilter]) -> Optional[Any]:
    try:
        query = supabase.table(table_name).select("*")
        result = makeFilter(query, filters).execute()
        return result
    except Exception as e:
        logger.error(f"查詢 {table_name} 時發生錯誤: {e}", exc_info=True)
        return None


# 帶分頁功能的日誌查詢
def get_logs_with_pagination(filters: List[DBFilter], limit: int = 50, offset: int = 0) -> Optional[Any]:
    """
    查詢日誌並支援分頁
    - filters: 篩選條件列表
    - limit: 每頁筆數
    - offset: 偏移量
    """
    try:
        query = supabase.table("TB_LOGS").select("*")
        query = makeFilter(query, filters)
        # 按日期和時間降序排列（最新的在前）
        query = query.order("date", desc=True).order("time", desc=True)
        # 分頁
        query = query.range(offset, offset + limit - 1)
        result = query.execute()
        return result
    except Exception as e:
        logger.error(f"查詢日誌分頁時發生錯誤: {e}", exc_info=True)
        return None


# 檢查Log是否超過一定次數(普通等級5次 高風險等級3次 緊急等級1次)
def need_send(log: Log) -> bool:
    try:
        # 根據風險等級判斷閾值
        threshold_map = {
            1: 5,  # 普通等級：5次
            2: 3,  # 高風險：3次
            3: 1   # 緊急：1次
        }
        threshold = threshold_map.get(log.riskLevel, 5)
        
        request = (
            supabase.table("TB_LOGS").select("*")
            .filter("location", Opreator.EQUAL, log.location)
            .filter("function", Opreator.EQUAL, log.function)
            .filter("log", Opreator.EQUAL, log.log)
            .filter("riskLevel", Opreator.EQUAL, log.riskLevel)
            .filter("count", Opreator.GREATER_OR_EQUAL, threshold)
            .execute()
        )
        return True if request.data and len(request.data) > 0 else False
    except Exception as e:
        logger.error(f"檢查是否需要發送通知時發生錯誤: {e}", exc_info=True)
        return False


# 新增Log資料
def insert_log(log: Log) -> Optional[Any]:
    try:
        # 手動轉換日期和時間為字串
        log_data = log.model_dump(exclude={'id'})  # 排除 id 欄位，讓資料庫自動生成
        log_data['date'] = log.date.isoformat()
        log_data['time'] = log.time.isoformat()
        result = supabase.table("TB_LOGS").insert(log_data).execute()
        # 如果是緊急等級直接通知相關人員
        if log.riskLevel == 3:
            try:
                message = Message(
                    title="系統緊急通知",
                    body=f"位置:{log.location}\n功能:{log.function}\n紀錄:{log.log}",
                    employees=log.employees
                )
                # 查詢剛剛新增的Log ID
                msg.send_message(message, result.data[0].get('id'))
            except Exception as e:
                logger.error(f"發送緊急通知時發生錯誤: {e}", exc_info=True)
        return result
    except Exception as e:
        logger.error(f"新增日誌時發生錯誤: {e}", exc_info=True)
        return None


# 更新Log資料
def update_log(log: Log) -> Optional[Any]:
    if log.id != None:
        try:
            # 手動轉換日期和時間為字串
            log_data = log.model_dump()
            log_data['date'] = log.date.isoformat()
            log_data['time'] = log.time.isoformat()
            result = update("TB_LOGS", log_data, [DBFilter(name="id", operator=Opreator.EQUAL, values=[str(log.id)])])
            # 如果超過一定次數通知相關人員(普通等級5次 高風險等級3次 緊急等級1次)
            if need_send(log):
                try:
                    message = Message(
                        title="系統通知",
                        body=f"位置:{log.location}\n功能:{log.function}\n紀錄:{log.log}\n次數:{log.count}",
                        employees=log.employees
                    )
                    msg.send_message(message, log.id)
                except Exception as e:
                    logger.error(f"發送通知時發生錯誤: {e}", exc_info=True)
            return result
        except Exception as e:
            logger.error(f"更新日誌時發生錯誤: {e}", exc_info=True)
            return None
    else:
        logger.warning("無法更新日誌: 缺少日誌 ID")
        return None


# 判斷是否為重複問題的Log
def check_log(log: Log) -> Optional[Log]:
    try:
        # 查詢資料庫中是否有相同log
        filters = [
            DBFilter(name="location", operator=Opreator.EQUAL, values=[log.location]),
            DBFilter(name="function", operator=Opreator.EQUAL, values=[log.function]),
            DBFilter(name="log", operator=Opreator.EQUAL, values=[log.log])
        ]
        response = call_by_filters("TB_LOGS", filters)
        if response and response.data and len(response.data) > 0:
            # 將字典轉換為 Log 物件
            data = response.data[0]
            return Log(
                id=data.get('id'),
                riskLevel=data.get('riskLevel'),
                type=data.get('type'),
                location=data.get('location'),
                function=data.get('function'),
                log=data.get('log'),
                employees=data.get('employees', []),
                date=data.get('date'),
                time=data.get('time'),
                count=data.get('count', 1)
            )
        return None
    except Exception as e:
        logger.error(f"檢查重複日誌時發生錯誤: {e}", exc_info=True)
        return None
