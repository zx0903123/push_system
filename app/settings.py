from pydantic import BaseSettings
from enum import Enum


class Settings(BaseSettings):
	"""全域設定（由 .env 檔案載入）

	說明: 包含應用名稱、DB/Redis 連線字串、推播服務設定等。
	請複製 .env.example 為 .env 並填入實際的設定值。
	"""

	# Supabase 設定
	SUPABASE_URL: str
	SUPABASE_KEY: str
	
	# Redis 設定
	REDIS_HOST: str
	REDIS_PORT: int = 6379
	REDIS_USERNAME: str = "default"
	REDIS_PASSWORD: str
	
	# 推播類型常數
	class Channel(str, Enum):
		EMAIL = 1
		LINE = 2
		TEAMS = 4
		SLACK = 8
		DISCORD = 16
		SMS = 32

	# 通知狀態常數
	class NotificationStatus(str, Enum):
		PENDING = 0      # 待發送
		SUCCESS = 1      # 成功
		FAILED = 2       # 失敗
		RETRYING = 3     # 重試中

	# 風險等級常數
	class RiskLevel(str, Enum):
		LOW = 1       # 普通
		HIGH = 2      # 高風險
		EMERGENCY = 3 # 緊急

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

