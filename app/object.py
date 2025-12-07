from pydantic import BaseModel
import datetime
from typing import List, Optional


class Log(BaseModel):
    id: Optional[int] = None
    riskLevel: int
    type: int
    location: str
    function: str
    log: str
    employees: List[str]
    date: datetime.date
    time: datetime.time
    count: int = 1
    
    class Config:
        """Pydantic 模型配置"""
        json_encoders = {
            datetime.date: lambda v: v.isoformat(),  # 將日期轉為 "2024-12-07" 格式
            datetime.time: lambda v: v.isoformat()   # 將時間轉為 "14:30:00" 格式
        }


class DBFilter(BaseModel):
    name: str
    operator: str
    values: List[str]


class Message(BaseModel):
    title: str
    body: str
    employees: List[str]


class EmployeeContact(BaseModel):
    id: int
    no: str
    name: str
    contactWay: int
    email: Optional[str] = None
    line: Optional[str] = None
    teams: Optional[str] = None
    slack: Optional[str] = None
    discord: Optional[str] = None
    phone: Optional[str] = None


class NotificationHistory(BaseModel):
    id: int
    log_id: int
    recipient: str
    message: str
    status: int
    error_message: str
    retry_count: int
    sent_at: datetime.datetime
