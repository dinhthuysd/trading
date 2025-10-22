import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

class Settings:
    # MongoDB
    MONGO_URL = os.environ['MONGO_URL']
    DB_NAME = os.environ.get('DB_NAME', 'document_exchange')
    
    # Security
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your-secret-key-change-in-production-min-32-chars-long')
    JWT_ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    REFRESH_TOKEN_EXPIRE_DAYS = 7
    
    # CORS
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE = 100
    
    # File Upload
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
    ALLOWED_FILE_TYPES = ['.pdf', '.doc', '.docx', '.txt', '.xls', '.xlsx', '.ppt', '.pptx', '.zip', '.rar']
    
    # Staking Plans
    STAKING_PLANS = {
        'basic': {'min_amount': 100, 'apy': 5, 'lock_days': 30},
        'premium': {'min_amount': 1000, 'apy': 10, 'lock_days': 90},
        'vip': {'min_amount': 10000, 'apy': 15, 'lock_days': 180}
    }
    
    # Investment Packages
    INVESTMENT_PACKAGES = {
        'starter': {'price': 500, 'expected_return': 8, 'duration_days': 60},
        'growth': {'price': 2000, 'expected_return': 12, 'duration_days': 90},
        'premium': {'price': 10000, 'expected_return': 18, 'duration_days': 180}
    }
    
    # Crypto (Mock)
    COINBASE_API_KEY = os.environ.get('COINBASE_API_KEY', 'mock-api-key')
    COINBASE_API_SECRET = os.environ.get('COINBASE_API_SECRET', 'mock-api-secret')
    WEB3_INFURA_URL = os.environ.get('WEB3_INFURA_URL', 'https://mainnet.infura.io/v3/mock')
    
    # Emergent Auth
    EMERGENT_SESSION_API = 'https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data'
    
settings = Settings()
