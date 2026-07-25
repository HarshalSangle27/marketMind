import os
import tempfile
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev_key_marketmind_2026'
    
    # Environment variable support for Vercel/Production deployment
    db_uri = os.environ.get('DATABASE_URL')
    if not db_uri:
        if os.environ.get('VERCEL'):
            db_path = os.path.join(tempfile.gettempdir(), 'marketmind.db')
            db_uri = f'sqlite:///{db_path}'
        else:
            db_uri = 'sqlite:///marketmind.db'
            
    # Fix for Postgres URLs starting with postgres:// instead of postgresql://
    if db_uri and db_uri.startswith("postgres://"):
        db_uri = db_uri.replace("postgres://", "postgresql://", 1)
        
    SQLALCHEMY_DATABASE_URI = db_uri
    SQLALCHEMY_TRACK_MODIFICATIONS = False