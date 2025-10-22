from functools import wraps
from fastapi import HTTPException, Request, status
from typing import Optional
from security import decode_token
from database import get_database
from datetime import datetime, timezone
from models import UserRole
import logging

logger = logging.getLogger(__name__)

# In-memory rate limiting (simple implementation)
rate_limit_storage = {}

def rate_limit(max_calls: int = 100, time_window: int = 60):
    """Rate limiting decorator"""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            client_ip = request.client.host
            current_time = datetime.now(timezone.utc).timestamp()
            
            if client_ip not in rate_limit_storage:
                rate_limit_storage[client_ip] = []
            
            # Remove old entries
            rate_limit_storage[client_ip] = [
                t for t in rate_limit_storage[client_ip] 
                if current_time - t < time_window
            ]
            
            if len(rate_limit_storage[client_ip]) >= max_calls:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please try again later."
                )
            
            rate_limit_storage[client_ip].append(current_time)
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

async def get_current_user(request: Request):
    """Get current authenticated user from token or session"""
    db = get_database()
    
    # Try to get session_token from cookie first
    session_token = request.cookies.get("session_token")
    
    if session_token:
        session = await db.sessions.find_one({"session_token": session_token})
        if session and session["expires_at"] > datetime.now(timezone.utc):
            user = await db.users.find_one({"id": session["user_id"]}, {"_id": 0})
            if user:
                return user
    
    # Try Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = auth_header.split(" ")[1]
    token_data = decode_token(token)
    
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = await db.users.find_one({"id": token_data.user_id}, {"_id": 0})
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user

async def get_optional_user(request: Request):
    """Get current user if authenticated, None otherwise"""
    try:
        return await get_current_user(request)
    except HTTPException:
        return None

async def require_admin(request: Request):
    """Require admin role"""
    user = await get_current_user(request)
    if user["role"] != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user

async def log_audit(db, user_id: Optional[str], action: str, details: dict, request: Request):
    """Log audit trail"""
    try:
        audit_log = {
            "user_id": user_id,
            "action": action,
            "details": details,
            "ip_address": request.client.host,
            "user_agent": request.headers.get("user-agent"),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await db.audit_logs.insert_one(audit_log)
    except Exception as e:
        logger.error(f"Failed to log audit: {e}")
