# -*- coding: utf-8 -*-
"""Email notification sender using SMTP."""
import logging
from typing import Optional, List
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.header import Header
from email.utils import formataddr
import smtplib

from src.config import Config
from src.formatters import markdown_to_html_document


logger = logging.getLogger(__name__)


# SMTP server presets for automatic detection.
SMTP_CONFIGS = {
    # QQ Mail.
    "qq.com": {"server": "smtp.qq.com", "port": 465, "ssl": True},
    "foxmail.com": {"server": "smtp.qq.com", "port": 465, "ssl": True},
    # NetEase Mail.
    "163.com": {"server": "smtp.163.com", "port": 465, "ssl": True},
    "126.com": {"server": "smtp.126.com", "port": 465, "ssl": True},
    # Gmail
    "gmail.com": {"server": "smtp.gmail.com", "port": 587, "ssl": False},
    # Outlook
    "outlook.com": {"server": "smtp-mail.outlook.com", "port": 587, "ssl": False},
    "hotmail.com": {"server": "smtp-mail.outlook.com", "port": 587, "ssl": False},
    "live.com": {"server": "smtp-mail.outlook.com", "port": 587, "ssl": False},
    # Sina Mail.
    "sina.com": {"server": "smtp.sina.com", "port": 465, "ssl": True},
    # Sohu Mail.
    "sohu.com": {"server": "smtp.sohu.com", "port": 465, "ssl": True},
    # Alibaba Cloud Mail.
    "aliyun.com": {"server": "smtp.aliyun.com", "port": 465, "ssl": True},
    # 139 Mail.
    "139.com": {"server": "smtp.139.com", "port": 465, "ssl": True},
}


class EmailSender:
    
    def __init__(self, config: Config):
        """Initialize email configuration."""
        self._email_config = {
            'sender': config.email_sender,
            'sender_name': getattr(config, 'email_sender_name', 'daily_stock_analysis Stock Analyst'),
            'password': config.email_password,
            'receivers': config.email_receivers or ([config.email_sender] if config.email_sender else []),
        }
        self._stock_email_groups = getattr(config, 'stock_email_groups', None) or []
        
    def _is_email_configured(self) -> bool:
        """Return whether email configuration is complete."""
        return bool(self._email_config['sender'] and self._email_config['password'])
    
    def get_receivers_for_stocks(self, stock_codes: List[str]) -> List[str]:
        """
        Look up email receivers for given stock codes based on stock_email_groups.
        Returns union of receivers for all matching groups; falls back to default if none match.
        """
        if not stock_codes or not self._stock_email_groups:
            return self._email_config['receivers']
        seen: set = set()
        result: List[str] = []
        for stocks, emails in self._stock_email_groups:
            for code in stock_codes:
                if code in stocks:
                    for e in emails:
                        if e not in seen:
                            seen.add(e)
                            result.append(e)
                    break
        return result if result else self._email_config['receivers']

    def get_all_email_receivers(self) -> List[str]:
        """
        Return union of all configured email receivers (all groups + default).
        Used for market review which should go to everyone.
        """
        seen: set = set()
        result: List[str] = []
        for _, emails in self._stock_email_groups:
            for e in emails:
                if e not in seen:
                    seen.add(e)
                    result.append(e)
        for e in self._email_config['receivers']:
            if e not in seen:
                seen.add(e)
                result.append(e)
        return result
    
    def send_to_email(
        self, content: str, subject: Optional[str] = None, receivers: Optional[List[str]] = None
    ) -> bool:
        """Send email via SMTP with automatic SMTP server detection."""
        if not self._is_email_configured():
            logger.warning("Email configuration is incomplete; skipping notification")
            return False
        
        sender = self._email_config['sender']
        password = self._email_config['password']
        receivers = receivers or self._email_config['receivers']
        
        try:
            # Generate subject.
            if subject is None:
                date_str = datetime.now().strftime('%Y-%m-%d')
                subject = f"📈 주식 AI 분석 리포트 - {date_str}"
            
            # Convert Markdown to simple HTML.
            html_content = markdown_to_html_document(content)
            
            # Build email message.
            msg = MIMEMultipart('alternative')
            msg['Subject'] = Header(subject, 'utf-8')
            msg['From'] = formataddr((self._email_config.get('sender_name', 'Stock Analyst'), sender))
            msg['To'] = ', '.join(receivers)
            
            # Add plain-text and HTML alternatives.
            text_part = MIMEText(content, 'plain', 'utf-8')
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Detect SMTP settings.
            domain = sender.split('@')[-1].lower()
            smtp_config = SMTP_CONFIGS.get(domain)
            
            if smtp_config:
                smtp_server = smtp_config['server']
                smtp_port = smtp_config['port']
                use_ssl = smtp_config['ssl']
                logger.info("Detected email domain: %s -> %s:%s", domain, smtp_server, smtp_port)
            else:
                # Unknown domain, try a generic SMTP host.
                smtp_server = f"smtp.{domain}"
                smtp_port = 465
                use_ssl = True
                logger.warning("Unknown email domain %s, trying generic SMTP: %s:%s", domain, smtp_server, smtp_port)
            
            # Select connection mode.
            if use_ssl:
                # SSL connection, usually port 465.
                server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=30)
            else:
                # TLS connection, usually port 587.
                server = smtplib.SMTP(smtp_server, smtp_port, timeout=30)
                server.starttls()
            
            server.login(sender, password)
            server.send_message(msg)
            server.quit()
            
            logger.info("Email sent successfully, receivers: %s", receivers)
            return True
            
        except smtplib.SMTPAuthenticationError:
            logger.error("Email send failed: authentication error, check sender account and app password")
            return False
        except smtplib.SMTPConnectError as e:
            logger.error("Email send failed: unable to connect to SMTP server - %s", e)
            return False
        except Exception as e:
            logger.error("Email send failed: %s", e)
            return False

    def _send_email_with_inline_image(
        self, image_bytes: bytes, receivers: Optional[List[str]] = None
    ) -> bool:
        """Send email with inline image attachment (Issue #289)."""
        if not self._is_email_configured():
            return False
        sender = self._email_config['sender']
        password = self._email_config['password']
        receivers = receivers or self._email_config['receivers']
        try:
            date_str = datetime.now().strftime('%Y-%m-%d')
            subject = f"📈 주식 AI 분석 리포트 - {date_str}"
            msg = MIMEMultipart('related')
            msg['Subject'] = Header(subject, 'utf-8')
            msg['From'] = formataddr(
                (self._email_config.get('sender_name', 'Stock Analyst'), sender)
            )
            msg['To'] = ', '.join(receivers)

            alt = MIMEMultipart('alternative')
            alt.attach(MIMEText('리포트가 생성되었습니다. 아래 이미지를 확인하세요.', 'plain', 'utf-8'))
            html_body = (
                '<p>리포트가 생성되었습니다. 아래 이미지를 확인하세요.</p>'
                '<p><img src="cid:report-image" alt="Stock analysis report" style="max-width:100%%;" /></p>'
            )
            alt.attach(MIMEText(html_body, 'html', 'utf-8'))
            msg.attach(alt)

            img_part = MIMEImage(image_bytes, _subtype='png')
            img_part.add_header('Content-Disposition', 'inline', filename='report.png')
            img_part.add_header('Content-ID', '<report-image>')
            msg.attach(img_part)

            domain = sender.split('@')[-1].lower()
            smtp_config = SMTP_CONFIGS.get(domain)
            if smtp_config:
                smtp_server, smtp_port = smtp_config['server'], smtp_config['port']
                use_ssl = smtp_config['ssl']
            else:
                smtp_server, smtp_port = f"smtp.{domain}", 465
                use_ssl = True

            if use_ssl:
                server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=30)
            else:
                server = smtplib.SMTP(smtp_server, smtp_port, timeout=30)
                server.starttls()
            server.login(sender, password)
            server.send_message(msg)
            server.quit()
            logger.info("Email with inline image sent successfully, receivers: %s", receivers)
            return True
        except Exception as e:
            logger.error("Email with inline image failed: %s", e)
            return False
