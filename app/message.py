from app.object import DBFilter, Message
from app.notification import NotificationHistory
import app.notification as notification
import app.database as db
import app.settings as settings
from app.settings import Channel, Status
from typing import List, Optional
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import requests
import logging
import time

logger = logging.getLogger(__name__)


# 發送通知
def send_message(message: Message, log_id: Optional[int] = None):
    """發送訊息給指定員工，支援多種通訊方式。"""
    emails = []
    line = False
    team = False
    slack = False
    discord = False
    phones = []

    # 用員工列表取得聯絡方式設定
    try:
        employees_contact = db.call_by_filters("TB_EMPLOYEE_CONTACT", [DBFilter(name="no", operator=db.Opreator.IN.value, values=message.employees)])
        
        if not employees_contact or not employees_contact.data:
            error_msg = f"找不到員工聯絡資訊: {message.employees}"
            logger.warning(error_msg)
            # 記錄查詢員工聯絡資訊失敗
            notification._save_notification_history(
                NotificationHistory(
                    log_id=log_id,
                    message=error_msg,
                    recipient=", ".join(message.employees),
                    status=settings.STATUS_FAILED,
                    error_message=error_msg
                )
            )
            return

        for contact in employees_contact.data:
            if contact.get('contactWay', 0) & settings.PUBLISHER_EMAIL:  # Email
                if contact.get('email'):
                    emails.append(contact['email'])
            if contact.get('contactWay', 0) & settings.PUBLISHER_LINE:  # Line
                line = True
            if contact.get('contactWay', 0) & settings.PUBLISHER_TEAMS:  # Teams
                team = True
            if contact.get('contactWay', 0) & settings.PUBLISHER_SLACK:  # Slack
                slack = True
            if contact.get('contactWay', 0) & settings.PUBLISHER_DISCORD:  # Discord
                discord = True
            if contact.get('contactWay', 0) & settings.PUBLISHER_SMS:  # SMS
                if contact.get('phone'):
                    phones.append(contact['phone'])

        # 如果有 Email 通知需求就發送 Email
        if len(emails) > 0:
            for email in emails:
                success = send_email(to=[email], subject=message.title, body=message.body, html=True, log_id=log_id)
                if not success:
                    logger.warning(f"Email 發送失敗: {email}")
        # 如果有 Line 通知需求就發送 Line
        if line:
            send_line(message.body, log_id=log_id)
        # 如果有 Teams 通知需求就發送 Teams
        if team:
            webhook(settings.PUBLISHER_TEAMS, message.body, log_id=log_id)
        # 如果有 Slack 通知需求就發送 Slack
        if slack:
            webhook(settings.PUBLISHER_SLACK, message.body, log_id=log_id)
        # 如果有 Discord 通知需求就發送 Discord
        if discord:
            webhook(settings.PUBLISHER_DISCORD, message.body, log_id=log_id)
        # 如果有 SMS 通知需求就發送簡訊
        if len(phones) > 0:
            sms(phones, message.body, log_id=log_id)
    
    except Exception as e:
        error_msg = f"發送訊息時發生錯誤: {e}"
        logger.error(error_msg, exc_info=True)
        # 記錄整體發送流程錯誤
        notification._save_notification_history(
            log_id=log_id,
            recipient=", ".join(message.employees) if message.employees else "Unknown",
            status=settings.STATUS_FAILED,
            error_message=error_msg
        )


# 發送Email通知
def send_email(to: List[str], subject: str, body: str, html: bool = False, attachments: Optional[List[str]] = None, log_id: Optional[int] = None):
    """
    發送 Email 的 function 並記錄通知歷史
    - to: 收件者清單
    - subject: 郵件主旨
    - body: 郵件內容
    - html: True 發 HTML 郵件, False 發文字郵件
    - attachments: 可附加檔案清單
    - log_id: 日誌 ID（用於記錄通知歷史）
    """
    error_msg = None
    retry_count = 0
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            message = MIMEMultipart()
            message["From"] = settings.SENDER_EMAIL
            message["To"] = ", ".join(to)
            message["Subject"] = subject

            # 郵件內容
            message.attach(MIMEText(body, "html" if html else "plain"))

            # 附檔
            if attachments:
                for filename in attachments:
                    with open(filename, "rb") as f:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header("Content-Disposition", f"attachment; filename={filename}")
                    message.attach(part)

            # 發送
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(settings.SENDER_EMAIL, settings.APP_PASSWORD)
                server.sendmail(settings.SENDER_EMAIL, to, message.as_string())

            logger.info(f"Email 已發送！收件者: {to}")
            notification._save_notification_history(
                log_id=log_id,
                message=f"Email 已發送！收件者: {', '.join(to)}",
                recipient=", ".join(to),
                status=Status.SUCCESS,
                retry_count=retry_count
            )
            return True
            
        except Exception as e:
            retry_count = attempt + 1
            error_msg = str(e)
            logger.error(f"Email 發送失敗 (嘗試 {retry_count}/{max_retries}): {e}", exc_info=True)
            if retry_count < max_retries:
                time.sleep(2 ** retry_count)
    
    # 所有重試都失敗
    notification._save_notification_history(
        log_id=log_id,
        message=f"Email 發送失敗 (嘗試 {max_retries} 次)",
        recipient=", ".join(to),
        status=settings.STATUS_FAILED,
        error_message=error_msg,
        retry_count=retry_count
    )
    return False


# 發送Line通知 目前只能推送到指定的一個群組或個人
def send_line(message: str, max_retries: int = 3, log_id: Optional[int] = None) -> bool:
    """發送 Line 訊息的 function 並記錄通知歷史"""
    if not settings.LINE_TOKEN:
        error_msg = "Line Token 未設定，跳過發送"
        logger.warning(error_msg)
        notification._save_notification_history(
            log_id=log_id,
            message=error_msg,
            recipient="Line Notify",
            status=settings.STATUS_FAILED,
            error_message=error_msg
        )
        return False
    
    error_msg = None
    for attempt in range(max_retries):
        try:
            headers = {"Authorization": f"Bearer {settings.LINE_TOKEN}"}
            payload = {"message": message}
            r = requests.post(settings.LINE_URL, headers=headers, data=payload, timeout=10)
            
            if r.status_code == 200:
                logger.info("Line 訊息已發送")
                notification._save_notification_history(
                    log_id=log_id,
                    message="Line 訊息已發送",
                    recipient="Line Notify",
                    status=Status.SUCCESS,
                    retry_count=attempt
                )
                return True
            else:
                error_msg = f"狀態碼: {r.status_code}, 回應: {r.text}"
                logger.error(f"Line 訊息發送失敗: {error_msg}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
        
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            logger.error(f"Line 請求失敗 (嘗試 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
    
    # 所有重試都失敗
    notification._save_notification_history(
        log_id=log_id,
        message=f"Email 發送失敗 (嘗試 {max_retries} 次)",
        recipient="Line Notify",
        status=settings.STATUS_FAILED,
        error_message=error_msg,
        retry_count=max_retries
    )
    return False


# 用Webhook發送Teams or slack or discords通知 目前只能推送到指定Url
def webhook(type: int, message: str, log_id: Optional[int] = None, max_retries: int = 3) -> bool:
    """發送 Teams/Slack/Discord 訊息的 function 並記錄通知歷史"""
    headers = {"Content-Type": "application/json"}
    payload = {"text": message}
    
    # 判斷通知渠道和 URL
    if type == settings.PUBLISHER_TEAMS:
        typeNam = "Teams"
        url = settings.TEAMS_URL
        channel = Channel.TEAMS
    elif type == settings.PUBLISHER_SLACK:
        typeNam = "Slack"
        url = settings.SLACK_URL
        channel = Channel.SLACK
    elif type == settings.PUBLISHER_DISCORD:
        typeNam = "Discord"
        url = settings.DISCORD_URL
        channel = Channel.DISCORD
    else:
        error_msg = f"不支援的 Webhook 類型: {type}"
        logger.warning(error_msg)
        return False
    
    if not url:
        error_msg = f"{typeNam} URL 未設定，跳過發送"
        logger.warning(error_msg)
        notification._save_notification_history(
            log_id=log_id,
            message=error_msg,
            recipient=typeNam,
            status=settings.STATUS_FAILED,
            error_message=error_msg
        )
        return False
    
    error_msg = None
    for attempt in range(max_retries):
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=10)
            
            if r.status_code in [200, 204]:
                logger.info(f"{typeNam} 訊息已發送！")
                notification._save_notification_history(
                    log_id=log_id,
                    message=f"{typeNam} 訊息已發送！",
                    recipient=typeNam,
                    status=Status.SUCCESS,
                    retry_count=attempt
                )
                return True
            else:
                error_msg = f"狀態碼: {r.status_code}, 回應: {r.text}"
                logger.error(f"{typeNam} 訊息發送失敗: {error_msg}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
        
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            logger.error(f"{typeNam} 請求失敗 (嘗試 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
    
    # 所有重試都失敗
    notification._save_notification_history(
        log_id=log_id,
        message=f"{typeNam} 發送失敗 (嘗試 {max_retries} 次)",
        recipient=typeNam,
        status=settings.STATUS_FAILED,
        error_message=error_msg,
        retry_count=max_retries
    )
    return False


# 使用SMS Gateway發送簡訊通知（免費但有限制）
def sms(phones: List[str], message: str, log_id: Optional[int] = None) -> bool:
    """發送簡訊的 function 並記錄通知歷史"""
    if not settings.EMAIL_TO_SMS_GATEWAY:
        error_msg = "SMS Gateway 未設定，跳過發送"
        logger.warning(error_msg)
        notification._save_notification_history(
            log_id=log_id,
            message=error_msg,
            recipient=", ".join(phones),
            status=settings.STATUS_FAILED,
            error_message=error_msg
        )
        return False
    
    success_count = 0
    failed_phones = []
    
    for phone in phones:
        try:
            receiver = phone + "@" + settings.EMAIL_TO_SMS_GATEWAY
            msg = MIMEText(message)
            msg['From'] = settings.SENDER_EMAIL
            msg['To'] = receiver
            msg['Subject'] = "簡訊通知"

            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as server:
                server.login(settings.SENDER_EMAIL, settings.APP_PASSWORD)
                server.send_message(msg)
            
            logger.info(f"簡訊已發送至 {phone}")
            success_count += 1
        
        except smtplib.SMTPException as e:
            logger.error(f"發送簡訊到 {phone} 失敗: {e}")
            failed_phones.append(phone)
        except Exception as e:
            logger.error(f"發送簡訊到 {phone} 時發生未預期的錯誤: {e}", exc_info=True)
            failed_phones.append(phone)
    
    # 記錄通知歷史
    if success_count > 0:
        notification._save_notification_history(
            log_id=log_id,
            message=f"簡訊已發送至 {', '.join(phones)}",
            recipient=", ".join(phones),
            status=Status.SUCCESS if success_count == len(phones) else settings.STATUS_FAILED,
            error_message=f"部分失敗: {', '.join(failed_phones)}" if failed_phones else None,
            retry_count=0
        )
    else:
        notification._save_notification_history(
            log_id=log_id,
            message=f"簡訊發送失敗至 {', '.join(phones)}",
            recipient=", ".join(phones),
            status=settings.STATUS_FAILED,
            error_message="所有收件者發送失敗",
            retry_count=0
        )
    
    return success_count > 0
