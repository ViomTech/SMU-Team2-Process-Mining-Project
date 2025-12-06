import os
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()

class Config:
    """Base configuration class."""
    SECRET_KEY = os.getenv('SECRET_KEY', 'default_secret')
    SECURITY_PASSWORD_SALT = os.getenv('SECURITY_PASSWORD_SALT', 'change-me')

    # --- Local/DB config (same as before) ---
    DB_NAME = os.getenv('DB_NAME', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = os.getenv('DB_PORT', 5432)

    SQLALCHEMY_DATABASE_URI = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- CORS / Frontend origins ---
    # Keep singular for backwards-compat, but prefer FRONTEND_ORIGINS (CSV)
    FRONTEND_ORIGIN = os.getenv('FRONTEND_ORIGIN', 'http://localhost:5173')
    FRONTEND_ORIGINS = [
        o.strip() for o in os.getenv('FRONTEND_ORIGINS', FRONTEND_ORIGIN).split(',')
        if o.strip()
    ]

    # --- Sessions ("Remember me") ---
    REMEMBER_ME_DAYS = int(os.getenv('REMEMBER_ME_DAYS', 7))
    PERMANENT_SESSION_LIFETIME = timedelta(days=REMEMBER_ME_DAYS)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.getenv('SESSION_COOKIE_SAMESITE', 'None')  # 'None' needed for cross-site cookies
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'false').lower() == 'true'  # set true in prod (HTTPS)

    # --- Password reset link target ---
    PASSWORD_RESET_URL = os.getenv('PASSWORD_RESET_URL', f'{FRONTEND_ORIGIN}/reset-password')

    # --- Gmail SMTP ---
    MAIL_FROM = os.getenv('MAIL_FROM', 'TripleThreatx2 <triplethreattimes2@gmail.com>')
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USERNAME = os.getenv('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', '')
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USE_SSL = os.getenv('MAIL_USE_SSL', 'false').lower() == 'true'

    # --- Hugging Face ---
    HF_API_KEY = os.getenv("HF_API_KEY")
    MODEL_NAME = os.getenv("MODEL_NAME", "deepseek-ai/DeepSeek-V3-0324")

    if not HF_API_KEY:
        raise ValueError("HF_API_KEY environment variable is not set.")
