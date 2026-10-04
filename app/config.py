import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'database/warehouse.db')
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    DEFAULT_CURRENCY = os.getenv('DEFAULT_CURRENCY', 'EGP')
