from fastapi import APIRouter, HTTPException, status, Request, Response, UploadFile, File
from models import (
    UserCreate, UserLogin, Token, User, TwoFactorSetup, TwoFactorVerify,
    PasswordResetRequest, PasswordReset, Session
)
from security import (
    hash_password, verify_password, create_access_token, 
    create_refresh_token, decode_token, generate_reset_token, hash_token
)
from database import get_database
from middleware import rate_limit, log_audit
from datetime import datetime, timedelta, timezone
import pyotp
import qrcode
import io
import base64
import httpx
from config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
@rate_limit(max_calls=10, time_window=300)  # 10 registrations per 5 minutes
async def register(user_data: UserCreate, request: Request):
    """Register a new user"""
    db = get_database()
    
    # Check if user exists
    existing_user = await db.users.find_one({
        "$or": [{"email": user_data.email}, {"username": user_data.username}]
    })
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or username already registered"
        )
    
    # Create user
    user = User(**user_data.model_dump(exclude={"password"}))
    user_dict = user.model_dump()
    user_dict["password_hash"] = hash_password(user_data.password)
    user_dict["created_at"] = user_dict["created_at"].isoformat()
    user_dict["updated_at"] = user_dict["updated_at"].isoformat()
    
    await db.users.insert_one(user_dict)
    
    # Create wallet for user
    wallet = {
        "user_id": user.id,
        "balance": 0.0,
        "locked_balance": 0.0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    await db.wallets.insert_one(wallet)
    
    # Create tokens
    access_token = create_access_token(
        data={"sub": user.id, "email": user.email, "role": user.role}
    )
    refresh_token = create_refresh_token(
        data={"sub": user.id, "email": user.email, "role": user.role}
    )
    
    await log_audit(db, user.id, "USER_REGISTERED", {"email": user.email}, request)
    
    return Token(access_token=access_token, refresh_token=refresh_token)

@router.post("/login", response_model=Token)
@rate_limit(max_calls=20, time_window=300)  # 20 logins per 5 minutes
async def login(login_data: UserLogin, request: Request, response: Response):
    """Login user"""
    db = get_database()
    
    # Find user
    user = await db.users.find_one({"email": login_data.email}, {"_id": 0})
    
    if not user or not verify_password(login_data.password, user["password_hash"]):
        await log_audit(db, None, "LOGIN_FAILED", {"email": login_data.email}, request)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Check if 2FA is enabled
    if user.get("is_2fa_enabled", False):
        if not login_data.totp_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="2FA code required"
            )
        
        totp = pyotp.TOTP(user["totp_secret"])
        if not totp.verify(login_data.totp_code):
            await log_audit(db, user["id"], "2FA_FAILED", {}, request)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid 2FA code"
            )
    
    # Create tokens
    access_token = create_access_token(
        data={"sub": user["id"], "email": user["email"], "role": user["role"]}
    )
    refresh_token = create_refresh_token(
        data={"sub": user["id"], "email": user["email"], "role": user["role"]}
    )
    
    await log_audit(db, user["id"], "USER_LOGIN", {}, request)
    
    return Token(access_token=access_token, refresh_token=refresh_token)

@router.post("/refresh", response_model=Token)
async def refresh_token(request: Request):
    """Refresh access token"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    token = auth_header.split(" ")[1]
    token_data = decode_token(token)
    
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    # Create new tokens
    access_token = create_access_token(
        data={"sub": token_data.user_id, "email": token_data.email, "role": token_data.role}
    )
    refresh_token = create_refresh_token(
        data={"sub": token_data.user_id, "email": token_data.email, "role": token_data.role}
    )
    
    return Token(access_token=access_token, refresh_token=refresh_token)

@router.post("/2fa/setup", response_model=TwoFactorSetup)
async def setup_2fa(request: Request):
    """Setup 2FA for user"""
    from middleware import get_current_user
    
    user = await get_current_user(request)
    
    # Generate secret
    secret = pyotp.random_base32()
    
    # Generate QR code
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(
        name=user["email"],
        issuer_name="Document Exchange"
    )
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    qr_code = base64.b64encode(buffer.getvalue()).decode()
    
    # Save secret temporarily (will be confirmed on verify)
    db = get_database()
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"totp_secret_temp": secret}}
    )
    
    await log_audit(db, user["id"], "2FA_SETUP_INITIATED", {}, request)
    
    return TwoFactorSetup(secret=secret, qr_code=f"data:image/png;base64,{qr_code}")

@router.post("/2fa/verify")
async def verify_2fa(verify_data: TwoFactorVerify, request: Request):
    """Verify and enable 2FA"""
    from middleware import get_current_user
    
    user = await get_current_user(request)
    db = get_database()
    
    user_data = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    
    if not user_data.get("totp_secret_temp"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA setup not initiated"
        )
    
    totp = pyotp.TOTP(user_data["totp_secret_temp"])
    if not totp.verify(verify_data.totp_code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid 2FA code"
        )
    
    # Enable 2FA
    await db.users.update_one(
        {"id": user["id"]},
        {
            "$set": {
                "totp_secret": user_data["totp_secret_temp"],
                "is_2fa_enabled": True
            },
            "$unset": {"totp_secret_temp": ""}
        }
    )
    
    await log_audit(db, user["id"], "2FA_ENABLED", {}, request)
    
    return {"success": True, "message": "2FA enabled successfully"}

@router.post("/2fa/disable")
async def disable_2fa(verify_data: TwoFactorVerify, request: Request):
    """Disable 2FA"""
    from middleware import get_current_user
    
    user = await get_current_user(request)
    db = get_database()
    
    user_data = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    
    if not user_data.get("is_2fa_enabled"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is not enabled"
        )
    
    totp = pyotp.TOTP(user_data["totp_secret"])
    if not totp.verify(verify_data.totp_code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid 2FA code"
        )
    
    # Disable 2FA
    await db.users.update_one(
        {"id": user["id"]},
        {
            "$set": {"is_2fa_enabled": False},
            "$unset": {"totp_secret": ""}
        }
    )
    
    await log_audit(db, user["id"], "2FA_DISABLED", {}, request)
    
    return {"success": True, "message": "2FA disabled successfully"}

@router.get("/google/login")
async def google_login(request: Request):
    """Redirect to Emergent Google OAuth"""
    frontend_url = request.headers.get("referer", "http://localhost:3000")
    redirect_url = f"{frontend_url}/dashboard"  # After auth, redirect to dashboard
    
    auth_url = f"https://auth.emergentagent.com/?redirect={redirect_url}"
    return {"auth_url": auth_url}

@router.post("/session")
async def create_session_from_google(request: Request, response: Response):
    """Create session from Google OAuth session_id"""
    db = get_database()
    
    # Get session_id from header
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session ID required"
        )
    
    # Call Emergent API to get session data
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                settings.EMERGENT_SESSION_API,
                headers={"X-Session-ID": session_id}
            )
            resp.raise_for_status()
            session_data = resp.json()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid session ID"
            )
    
    # Check if user exists
    user = await db.users.find_one({"email": session_data["email"]}, {"_id": 0})
    
    if not user:
        # Create new user from Google data
        new_user = User(
            email=session_data["email"],
            username=session_data["email"].split("@")[0],
            full_name=session_data.get("name", "")
        )
        user_dict = new_user.model_dump()
        user_dict["password_hash"] = ""  # No password for OAuth users
        user_dict["created_at"] = user_dict["created_at"].isoformat()
        user_dict["updated_at"] = user_dict["updated_at"].isoformat()
        
        await db.users.insert_one(user_dict)
        
        # Create wallet
        wallet = {
            "user_id": new_user.id,
            "balance": 0.0,
            "locked_balance": 0.0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.wallets.insert_one(wallet)
        
        user = user_dict
        await log_audit(db, new_user.id, "USER_REGISTERED_OAUTH", {"email": session_data["email"]}, request)
    
    # Create session
    session_token = session_data["session_token"]
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    
    session = Session(
        user_id=user["id"],
        session_token=session_token,
        expires_at=expires_at
    )
    
    session_dict = session.model_dump()
    session_dict["expires_at"] = session_dict["expires_at"].isoformat()
    session_dict["created_at"] = session_dict["created_at"].isoformat()
    
    await db.sessions.insert_one(session_dict)
    
    # Set cookie
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=7 * 24 * 60 * 60,  # 7 days
        path="/"
    )
    
    await log_audit(db, user["id"], "USER_LOGIN_OAUTH", {}, request)
    
    return {
        "success": True,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "username": user["username"],
            "full_name": user.get("full_name"),
            "role": user["role"]
        }
    }

@router.post("/logout")
async def logout(request: Request, response: Response):
    """Logout user"""
    from middleware import get_current_user
    
    user = await get_current_user(request)
    db = get_database()
    
    # Delete session if exists
    session_token = request.cookies.get("session_token")
    if session_token:
        await db.sessions.delete_one({"session_token": session_token})
        response.delete_cookie("session_token", path="/")
    
    await log_audit(db, user["id"], "USER_LOGOUT", {}, request)
    
    return {"success": True, "message": "Logged out successfully"}
