from pydantic_settings import BaseSettings
from enum import Enum


# 推播類型常數（用於位元運算）
PUBLISHER_EMAIL = 1
PUBLISHER_LINE = 2
PUBLISHER_TEAMS = 4
PUBLISHER_SLACK = 8
PUBLISHER_DISCORD = 16
PUBLISHER_SMS = 32

# 推播類型常數
PUBLISHER_EMAIL = 1
PUBLISHER_LINE = 2
PUBLISHER_TEAMS = 4
PUBLISHER_SLACK = 8
PUBLISHER_DISCORD = 16
PUBLISHER_SMS = 32

# 通知狀態常數
STATUS_PENDING = 0      # 待發送
STATUS_SUCCESS = 1      # 成功
STATUS_FAILED = 2       # 失敗
STATUS_RETRYING = 3     # 重試中

# 風險等級常數
RISK_LEVEL_LOW = 1       # 普通
RISK_LEVEL_HIGH = 2      # 高風險
RISK_LEVEL_EMERGENCY = 3 # 緊急


# 通知渠道枚舉（用於歷史記錄）
class Channel(str, Enum):
	EMAIL = "Email"
	LINE = "Line"
	TEAMS = "Teams"
	SLACK = "Slack"
	DISCORD = "Discord"
	SMS = "SMS"


# 通知狀態枚舉
class Status(str, Enum):
	PENDING = "Pending"      # 待發送
	SUCCESS = "Success"      # 成功
	FAILED = "Failed"        # 失敗
	RETRYING = "Retrying"    # 重試中


class Settings(BaseSettings):
	"""全域設定（由 .env 檔案載入）

	說明: 包含應用名稱、DB/Redis 連線字串、推播服務設定等。
	請複製 .env.example 為 .env 並填入實際的設定值。
	"""

	# Debug 模式
	DEBUG: int = 0

	# Supabase 設定
	SUPABASE_URL: str
	SUPABASE_KEY: str
	
	# Redis 設定
	REDIS_HOST: str
	REDIS_PORT: int = 6379
	REDIS_USERNAME: str = "default"
	REDIS_PASSWORD: str

	# Email 設定
	SENDER_EMAIL: str
	APP_PASSWORD: str
	
	# Line Notify 設定
	LINE_URL: str = "https://notify-api.line.me/api/notify"
	LINE_TOKEN: str = ""
	
	# Webhook 設定
	TEAMS_URL: str = ""
	SLACK_URL: str = ""
	DISCORD_URL: str = ""
	
	# SMS Gateway 設定
	EMAIL_TO_SMS_GATEWAY: str = ""
	
	class Config:
		env_file = ".env"
		env_file_encoding = "utf-8"
		case_sensitive = False
	

settings = Settings()

