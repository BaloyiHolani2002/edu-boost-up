import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-123')
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///eduboostup.db')
    DEBUG = True