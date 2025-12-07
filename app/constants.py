from enum import Enum


# 推播類型常數（用於位元運算）
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
