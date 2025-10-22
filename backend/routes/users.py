from fastapi import APIRouter, HTTPException, status, Request, UploadFile, File
from models import UserProfile, KYCSubmission, KYCStatus
from middleware import get_current_user, rate_limit, log_audit
from database import get_database, get_gridfs
from datetime import datetime, timezone
import base64

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/profile", response_model=UserProfile)
async def get_profile(request: Request):
    """Get user profile"""
    user = await get_current_user(request)
    
    return UserProfile(
        id=user["id"],
        email=user["email"],
        username=user["username"],
        full_name=user.get("full_name"),
        phone=user.get("phone"),
        role=user["role"],
        kyc_status=user["kyc_status"],
        is_2fa_enabled=user.get("is_2fa_enabled", False),
        created_at=datetime.fromisoformat(user["created_at"]) if isinstance(user["created_at"], str) else user["created_at"]
    )

@router.put("/profile")
async def update_profile(request: Request, full_name: str = None, phone: str = None):
    """Update user profile"""
    user = await get_current_user(request)
    db = get_database()
    
    update_data = {}
    if full_name is not None:
        update_data["full_name"] = full_name
    if phone is not None:
        update_data["phone"] = phone
    
    if update_data:
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        await db.users.update_one(
            {"id": user["id"]},
            {"$set": update_data}
        )
    
    await log_audit(db, user["id"], "PROFILE_UPDATED", update_data, request)
    
    return {"success": True, "message": "Profile updated successfully"}

@router.post("/kyc")
@rate_limit(max_calls=5, time_window=3600)  # 5 submissions per hour
async def submit_kyc(
    request: Request,
    id_type: str = "id_card",
    id_number: str = "",
    id_front: UploadFile = File(...),
    id_back: UploadFile = File(None),
    selfie: UploadFile = File(...),
    address_proof: UploadFile = File(None)
):
    """Submit KYC documents"""
    user = await get_current_user(request)
    db = get_database()
    fs = get_gridfs()
    
    # Check if already verified
    if user["kyc_status"] == KYCStatus.VERIFIED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="KYC already verified"
        )
    
    # Upload files to GridFS
    id_front_content = await id_front.read()
    id_front_id = await fs.upload_from_stream(
        f"kyc_{user['id']}_id_front",
        id_front_content,
        metadata={"user_id": user["id"], "type": "kyc_id_front"}
    )
    
    selfie_content = await selfie.read()
    selfie_id = await fs.upload_from_stream(
        f"kyc_{user['id']}_selfie",
        selfie_content,
        metadata={"user_id": user["id"], "type": "kyc_selfie"}
    )
    
    id_back_id = None
    if id_back:
        id_back_content = await id_back.read()
        id_back_id = await fs.upload_from_stream(
            f"kyc_{user['id']}_id_back",
            id_back_content,
            metadata={"user_id": user["id"], "type": "kyc_id_back"}
        )
    
    address_proof_id = None
    if address_proof:
        address_proof_content = await address_proof.read()
        address_proof_id = await fs.upload_from_stream(
            f"kyc_{user['id']}_address_proof",
            address_proof_content,
            metadata={"user_id": user["id"], "type": "kyc_address_proof"}
        )
    
    # Save KYC submission
    kyc_data = {
        "user_id": user["id"],
        "id_type": id_type,
        "id_number": id_number,
        "id_front_file_id": str(id_front_id),
        "id_back_file_id": str(id_back_id) if id_back_id else None,
        "selfie_file_id": str(selfie_id),
        "address_proof_file_id": str(address_proof_id) if address_proof_id else None,
        "status": KYCStatus.PENDING,
        "submitted_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.kyc_submissions.insert_one(kyc_data)
    
    # Update user KYC status
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"kyc_status": KYCStatus.PENDING}}
    )
    
    await log_audit(db, user["id"], "KYC_SUBMITTED", {"id_type": id_type}, request)
    
    return {"success": True, "message": "KYC documents submitted successfully"}

@router.get("/kyc/status")
async def get_kyc_status(request: Request):
    """Get KYC status"""
    user = await get_current_user(request)
    db = get_database()
    
    kyc_submission = await db.kyc_submissions.find_one(
        {"user_id": user["id"]},
        {"_id": 0},
        sort=[("submitted_at", -1)]
    )
    
    return {
        "status": user["kyc_status"],
        "submission": kyc_submission
    }
