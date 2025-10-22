from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
from config import settings
import logging

logger = logging.getLogger(__name__)

class Database:
    client: AsyncIOMotorClient = None
    db = None
    fs = None  # GridFS

db_instance = Database()

async def connect_to_mongo():
    """Connect to MongoDB"""
    logger.info("Connecting to MongoDB...")
    db_instance.client = AsyncIOMotorClient(settings.MONGO_URL)
    db_instance.db = db_instance.client[settings.DB_NAME]
    db_instance.fs = AsyncIOMotorGridFSBucket(db_instance.db)
    logger.info("Connected to MongoDB successfully")
    
    # Create indexes
    await create_indexes()

async def close_mongo_connection():
    """Close MongoDB connection"""
    logger.info("Closing MongoDB connection...")
    db_instance.client.close()
    logger.info("MongoDB connection closed")

async def create_indexes():
    """Create database indexes for performance and security"""
    db = db_instance.db
    
    # Users indexes
    await db.users.create_index("email", unique=True)
    await db.users.create_index("username", unique=True)
    await db.users.create_index("created_at")
    
    # Sessions indexes
    await db.sessions.create_index("session_token", unique=True)
    await db.sessions.create_index("user_id")
    await db.sessions.create_index("expires_at")
    
    # Documents indexes
    await db.documents.create_index("seller_id")
    await db.documents.create_index("category")
    await db.documents.create_index("status")
    await db.documents.create_index("created_at")
    
    # Transactions indexes
    await db.transactions.create_index("user_id")
    await db.transactions.create_index("type")
    await db.transactions.create_index("created_at")
    
    # Wallets indexes
    await db.wallets.create_index("user_id", unique=True)
    
    # Audit logs indexes
    await db.audit_logs.create_index("user_id")
    await db.audit_logs.create_index("action")
    await db.audit_logs.create_index("timestamp")
    
    logger.info("Database indexes created successfully")

def get_database():
    return db_instance.db

def get_gridfs():
    return db_instance.fs
