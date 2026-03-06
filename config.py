import os
from dotenv import load_dotenv

# Load environment variables from .env file for local development
load_dotenv()


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'super-secret-ipl-key-2026'
    
    # Database
    # Default to a local SQLite database if DATABASE_URL is not set (e.g. for local dev)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    
    # Render provides connection string starting with postgres:// but SQLAlchemy requires postgresql://
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace("postgres://", "postgresql://", 1)
        
    if not SQLALCHEMY_DATABASE_URI:
        SQLALCHEMY_DATABASE_URI = 'sqlite:///auction.db'
        
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Ensure template changes are picked up immediately
    TEMPLATES_AUTO_RELOAD = True
