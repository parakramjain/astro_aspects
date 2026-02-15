from email.mime.multipart import MIMEMultipart
import smtplib
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from email.message import EmailMessage
from html import escape as html_escape
import os
from dotenv import load_dotenv

load_dotenv()

# Security
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
APP_SECRET = os.getenv("APP_SECRET", "super-secret-key-change-me")

# Email
EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "console") # console, sendgrid, smtp
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "") # App password
EMAIL_FROM = os.getenv("EMAIL_FROM", "parakramjain@gmail.com")
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "")

def send_email(to_email: str, subject: str, body: str, pdf_path: str, html_body: str | None = None):
    msg = EmailMessage()
    if EMAIL_FROM_NAME:
        msg['From'] = f"{EMAIL_FROM_NAME} <{EMAIL_FROM}>"
    else:
        msg['From'] = EMAIL_FROM
    msg['To'] = to_email
    msg['Subject'] = subject

    msg.set_content(body or "", subtype="plain", charset="utf-8")
    if html_body is None:
        safe = html_escape(body or "")
        html_body = (
            "<html><body>"
            + safe.replace("\n", "<br>")
            + "</body></html>"
        )
    msg.add_alternative(html_body, subtype="html", charset="utf-8")

    if pdf_path:
        with open(pdf_path, 'rb') as attachment:
            msg.add_attachment(attachment.read(), maintype='application', subtype='pdf', filename=os.path.basename(pdf_path))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)