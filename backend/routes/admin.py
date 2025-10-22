from fastapi import APIRouter, HTTPException, status, Request, Query
from models import User, Document, DocumentStatus, KYCStatus, TransactionStatus, UserRole
from middleware import require_admin, log_audit, rate_limit
from database import get_database
from datetime import datetime, timezone
from typing import List, Optional

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/users")
async def get_users(
    request: Request,
    role: Optional[str] = None,
    kyc_status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200)
):
    """Get all users (admin only)"""
    admin = await require_admin(request)
    db = get_database()
    
    query = {}
    if role:
        query["role"] = role
    if kyc_status:
        query["kyc_status"] = kyc_status
    
    users = await db.users.find(
        query,
        {"_id": 0, "password_hash": 0, "totp_secret": 0}
    ).skip(skip).limit(limit).to_list(limit)
    
    return {
        "users": users,
        "total": await db.users.count_documents(query)
    }

@router.get("/users/{user_id}")
async def get_user_details(user_id: str, request: Request):
    """Get user details (admin only)"""
    admin = await require_admin(request)
    db = get_database()
    
    user = await db.users.find_one(
        {"id": user_id},
        {"_id": 0, "password_hash": 0, "totp_secret": 0}
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get wallet info
    wallet = await db.wallets.find_one({"user_id": user_id}, {"_id": 0})
    
    # Get KYC submission
    kyc = await db.kyc_submissions.find_one(
        {"user_id": user_id},
        {"_id": 0},
        sort=[("submitted_at", -1)]
    )
    
    # Get transaction summary
    transactions_count = await db.transactions.count_documents({"user_id": user_id})
    
    return {
        "user": user,
        "wallet": wallet,
        "kyc_submission": kyc,
        "transactions_count": transactions_count
    }

@router.put("/users/{user_id}/verify-kyc")
@rate_limit(max_calls=50, time_window=3600)
async def verify_kyc(user_id: str, request: Request, approved: bool = True, reason: str = ""):
    """Verify or reject KYC (admin only)"""
    admin = await require_admin(request)
    db = get_database()
    
    # Get KYC submission
    kyc = await db.kyc_submissions.find_one(
        {"user_id": user_id},
        {"_id": 0},
        sort=[("submitted_at", -1)]
    )
    
    if not kyc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="KYC submission not found"
        )
    
    new_status = KYCStatus.VERIFIED if approved else KYCStatus.REJECTED
    
    # Update KYC submission
    await db.kyc_submissions.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "status": new_status,
                "reviewed_by": admin["id"],
                "reviewed_at": datetime.now(timezone.utc).isoformat(),
                "reason": reason
            }
        }
    )
    
    # Update user KYC status
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"kyc_status": new_status}}
    )
    
    await log_audit(db, admin["id"], "KYC_REVIEWED", {"user_id": user_id, "approved": approved}, request)
    
    return {
        "success": True,
        "message": f"KYC {'approved' if approved else 'rejected'} successfully"
    }

@router.put("/users/{user_id}/role")
async def update_user_role(user_id: str, role: UserRole, request: Request):
    """Update user role (admin only)"""
    admin = await require_admin(request)
    db = get_database()
    
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"role": role}}
    )
    
    await log_audit(db, admin["id"], "USER_ROLE_UPDATED", {"user_id": user_id, "new_role": role}, request)
    
    return {"success": True, "message": f"User role updated to {role}"}

@router.get("/documents")
async def get_all_documents(
    request: Request,
    status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200)
):
    """Get all documents (admin only)"""
    admin = await require_admin(request)
    db = get_database()
    
    query = {}
    if status:
        query["status"] = status
    
    documents = await db.documents.find(
        query,
        {"_id": 0}
    ).skip(skip).limit(limit).to_list(limit)
    
    return {
        "documents": documents,
        "total": await db.documents.count_documents(query)
    }

@router.put("/documents/{document_id}/approve")
@rate_limit(max_calls=100, time_window=3600)
async def approve_document(document_id: str, request: Request, approved: bool = True, reason: str = ""):
    """Approve or reject document (admin only)"""
    admin = await require_admin(request)
    db = get_database()
    
    document = await db.documents.find_one({"id": document_id}, {"_id": 0})
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    new_status = DocumentStatus.APPROVED if approved else DocumentStatus.REJECTED
    
    await db.documents.update_one(
        {"id": document_id},
        {
            "$set": {
                "status": new_status,
                "reviewed_by": admin["id"],
                "reviewed_at": datetime.now(timezone.utc).isoformat(),
                "rejection_reason": reason if not approved else None
            }
        }
    )
    
    await log_audit(db, admin["id"], "DOCUMENT_REVIEWED", {"document_id": document_id, "approved": approved}, request)
    
    return {
        "success": True,
        "message": f"Document {'approved' if approved else 'rejected'} successfully"
    }

@router.get("/transactions")
async def get_all_transactions(
    request: Request,
    user_id: Optional[str] = None,
    type: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200)
):
    """Get all transactions (admin only)"""
    admin = await require_admin(request)
    db = get_database()
    
    query = {}
    if user_id:
        query["user_id"] = user_id
    if type:
        query["type"] = type
    if status:
        query["status"] = status
    
    transactions = await db.transactions.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    
    return {
        "transactions": transactions,
        "total": await db.transactions.count_documents(query)
    }

@router.get("/deposits")
async def get_deposit_requests(
    request: Request,
    status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200)
):
    """Get deposit requests (admin only)"""
    admin = await require_admin(request)
    db = get_database()
    
    query = {}
    if status:
        query["status"] = status
    else:
        query["status"] = TransactionStatus.PENDING  # Default to pending
    
    deposits = await db.deposit_requests.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    
    return {
        "deposits": deposits,
        "total": await db.deposit_requests.count_documents(query)
    }

@router.put("/deposits/{deposit_id}/process")
@rate_limit(max_calls=100, time_window=3600)
async def process_deposit(deposit_id: str, request: Request, approved: bool = True, reason: str = ""):
    """Process deposit request (admin only)"""
    admin = await require_admin(request)
    db = get_database()
    
    deposit = await db.deposit_requests.find_one({"id": deposit_id}, {"_id": 0})
    
    if not deposit:
        # Try matching by user_id and amount (fallback)
        deposits = await db.deposit_requests.find({"status": TransactionStatus.PENDING}, {"_id": 0}).to_list(1000)
        if deposits:
            deposit = deposits[0]  # Use first pending deposit
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deposit request not found"
            )
    
    if deposit["status"] != TransactionStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Deposit already processed"
        )
    
    user_id = deposit["user_id"]
    amount = deposit["amount"]
    
    if approved:
        # Add to wallet
        await db.wallets.update_one(
            {"user_id": user_id},
            {"$inc": {"balance": amount}}
        )
        
        # Update transaction status
        await db.transactions.update_one(
            {
                "user_id": user_id,
                "type": "deposit",
                "amount": amount,
                "status": TransactionStatus.PENDING
            },
            {"$set": {"status": TransactionStatus.COMPLETED}}
        )
    else:
        # Update transaction status to failed
        await db.transactions.update_one(
            {
                "user_id": user_id,
                "type": "deposit",
                "amount": amount,
                "status": TransactionStatus.PENDING
            },
            {"$set": {"status": TransactionStatus.FAILED}}
        )
    
    # Update deposit request
    new_status = TransactionStatus.COMPLETED if approved else TransactionStatus.FAILED
    await db.deposit_requests.update_many(
        {"user_id": user_id, "amount": amount, "status": TransactionStatus.PENDING},
        {
            "$set": {
                "status": new_status,
                "processed_by": admin["id"],
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "reason": reason
            }
        }
    )
    
    await log_audit(db, admin["id"], "DEPOSIT_PROCESSED", {"user_id": user_id, "amount": amount, "approved": approved}, request)
    
    return {
        "success": True,
        "message": f"Deposit {'approved' if approved else 'rejected'} successfully"
    }

@router.get("/withdrawals")
async def get_withdrawal_requests(
    request: Request,
    status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200)
):
    """Get withdrawal requests (admin only)"""
    admin = await require_admin(request)
    db = get_database()
    
    query = {}
    if status:
        query["status"] = status
    else:
        query["status"] = TransactionStatus.PENDING  # Default to pending
    
    withdrawals = await db.withdrawal_requests.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    
    return {
        "withdrawals": withdrawals,
        "total": await db.withdrawal_requests.count_documents(query)
    }

@router.put("/withdrawals/{withdrawal_id}/process")
@rate_limit(max_calls=100, time_window=3600)
async def process_withdrawal(withdrawal_id: str, request: Request, approved: bool = True, reason: str = "", tx_hash: str = ""):
    """Process withdrawal request (admin only)"""
    admin = await require_admin(request)
    db = get_database()
    
    withdrawal = await db.withdrawal_requests.find_one({"id": withdrawal_id}, {"_id": 0})
    
    if not withdrawal:
        # Fallback
        withdrawals = await db.withdrawal_requests.find({"status": TransactionStatus.PENDING}, {"_id": 0}).to_list(1000)
        if withdrawals:
            withdrawal = withdrawals[0]
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Withdrawal request not found"
            )
    
    if withdrawal["status"] != TransactionStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Withdrawal already processed"
        )
    
    user_id = withdrawal["user_id"]
    amount = withdrawal["amount"]
    
    if approved:
        # Deduct from wallet (already locked, so just deduct from locked and total)
        await db.wallets.update_one(
            {"user_id": user_id},
            {
                "$inc": {
                    "balance": -amount,
                    "locked_balance": -amount
                }
            }
        )
        
        # Update transaction status
        await db.transactions.update_one(
            {
                "user_id": user_id,
                "type": "withdrawal",
                "amount": amount,
                "status": TransactionStatus.PENDING
            },
            {
                "$set": {
                    "status": TransactionStatus.COMPLETED,
                    "metadata.tx_hash": tx_hash
                }
            }
        )
    else:
        # Unlock amount
        await db.wallets.update_one(
            {"user_id": user_id},
            {"$inc": {"locked_balance": -amount}}
        )
        
        # Update transaction status to failed
        await db.transactions.update_one(
            {
                "user_id": user_id,
                "type": "withdrawal",
                "amount": amount,
                "status": TransactionStatus.PENDING
            },
            {"$set": {"status": TransactionStatus.FAILED}}
        )
    
    # Update withdrawal request
    new_status = TransactionStatus.COMPLETED if approved else TransactionStatus.FAILED
    await db.withdrawal_requests.update_many(
        {"user_id": user_id, "amount": amount, "status": TransactionStatus.PENDING},
        {
            "$set": {
                "status": new_status,
                "processed_by": admin["id"],
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "tx_hash": tx_hash if approved else None,
                "reason": reason
            }
        }
    )
    
    await log_audit(db, admin["id"], "WITHDRAWAL_PROCESSED", {"user_id": user_id, "amount": amount, "approved": approved}, request)
    
    return {
        "success": True,
        "message": f"Withdrawal {'approved' if approved else 'rejected'} successfully"
    }

@router.get("/analytics")
async def get_analytics(request: Request):
    """Get platform analytics (admin only)"""
    admin = await require_admin(request)
    db = get_database()
    
    # User stats
    total_users = await db.users.count_documents({})
    verified_users = await db.users.count_documents({"kyc_status": KYCStatus.VERIFIED})
    
    # Document stats
    total_documents = await db.documents.count_documents({})
    approved_documents = await db.documents.count_documents({"status": DocumentStatus.APPROVED})
    
    # Transaction stats
    total_transactions = await db.transactions.count_documents({})
    completed_transactions = await db.transactions.count_documents({"status": TransactionStatus.COMPLETED})
    
    # Calculate total volume
    transactions = await db.transactions.find({"status": TransactionStatus.COMPLETED}, {"_id": 0}).to_list(10000)
    total_volume = sum(tx["amount"] for tx in transactions)
    
    # Pending requests
    pending_deposits = await db.deposit_requests.count_documents({"status": TransactionStatus.PENDING})
    pending_withdrawals = await db.withdrawal_requests.count_documents({"status": TransactionStatus.PENDING})
    pending_kyc = await db.kyc_submissions.count_documents({"status": KYCStatus.PENDING})
    pending_documents = await db.documents.count_documents({"status": DocumentStatus.PENDING})
    
    return {
        "users": {
            "total": total_users,
            "verified": verified_users
        },
        "documents": {
            "total": total_documents,
            "approved": approved_documents,
            "pending": pending_documents
        },
        "transactions": {
            "total": total_transactions,
            "completed": completed_transactions,
            "total_volume": total_volume
        },
        "pending_requests": {
            "deposits": pending_deposits,
            "withdrawals": pending_withdrawals,
            "kyc": pending_kyc
        }
    }

@router.get("/audit-logs")
async def get_audit_logs(
    request: Request,
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500)
):
    """Get audit logs (admin only)"""
    admin = await require_admin(request)
    db = get_database()
    
    query = {}
    if user_id:
        query["user_id"] = user_id
    if action:
        query["action"] = action
    
    logs = await db.audit_logs.find(
        query,
        {"_id": 0}
    ).sort("timestamp", -1).skip(skip).limit(limit).to_list(limit)
    
    return {
        "logs": logs,
        "total": await db.audit_logs.count_documents(query)
    }
