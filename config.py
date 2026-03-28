import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev_key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///marketmind.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False