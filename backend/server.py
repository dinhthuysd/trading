from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from database import connect_to_mongo, close_mongo_connection
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Document Exchange API",
    description="Secure document trading platform with cryptocurrency integration",
    version="1.0.0"
)

# Create API router with /api prefix
api_router = APIRouter(prefix="/api")

# Import routes
from routes import auth, users, documents, wallets, crypto, staking, investments, document_investments, admin

# Include all routes
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(documents.router)
api_router.include_router(wallets.router)
api_router.include_router(crypto.router)
api_router.include_router(staking.router)
api_router.include_router(investments.router)
api_router.include_router(document_investments.router)
api_router.include_router(admin.router)

# Root endpoint
@api_router.get("/")
async def root():
    return {
        "message": "Document Exchange API",
        "version": "1.0.0",
        "status": "operational"
    }

@api_router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": "connected"
    }

# Include router in app
app.include_router(api_router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info("Starting Document Exchange API...")
    await connect_to_mongo()
    logger.info("Document Exchange API started successfully")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Document Exchange API...")
    await close_mongo_connection()
    logger.info("Document Exchange API shut down successfully")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
