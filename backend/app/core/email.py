"""
Email service for password reset and notifications
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from app.core.config import settings

def send_password_reset_email(email: str, name: str, reset_token: str) -> bool:
    """Send password reset email"""
    if not settings.SMTP_ENABLED:
        return False
    
    reset_link = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
    
    subject = "Password Reset Request"
    body = f"""
    Hi {name},
    
    You requested a password reset for your HR Intake Platform account.
    
    Click the link below to reset your password:
    {reset_link}
    
    This link will expire in 1 hour.
    
    If you didn't request this, please ignore this email.
    
    Best regards,
    HR Intake Platform Team
    """
    
    return _send_email(email, subject, body)

def send_welcome_email(email: str, name: str, organization_name: str) -> bool:
    """Send welcome email to new user"""
    if not settings.SMTP_ENABLED:
        return False
    
    subject = f"Welcome to HR Intake Platform - {organization_name}"
    body = f"""
    Hi {name},
    
    Welcome to the HR Intake Platform for {organization_name}!
    
    Your account has been successfully created. You can now log in using your credentials.
    
    Login URL: {settings.FRONTEND_URL}/login
    
    If you have any questions, please contact your administrator.
    
    Best regards,
    HR Intake Platform Team
    """
    
    return _send_email(email, subject, body)

def _send_email(to_email: str, subject: str, body: str) -> bool:
    """Internal function to send email via SMTP"""
    try:
        msg = MIMEMultipart()
        msg["From"] = settings.SMTP_FROM_EMAIL
        msg["To"] = to_email
        msg["Subject"] = subject
        
        msg.attach(MIMEText(body, "plain"))
        
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_TLS:
                server.starttls()
            if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(msg)
        
        return True
    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        return False