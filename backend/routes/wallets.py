from fastapi import APIRouter, HTTPException, status, Request, Query
from models import Wallet, DepositRequest, WithdrawalRequest, Transaction, TransactionType, TransactionStatus
from middleware import get_current_user, rate_limit, log_audit
from database import get_database
from datetime import datetime, timezone
from typing import List

router = APIRouter(prefix="/wallets", tags=["Wallets"])

@router.get("/balance")
async def get_balance(request: Request):
    """Get wallet balance"""
    user = await get_current_user(request)
    db = get_database()
    
    wallet = await db.wallets.find_one({"user_id": user["id"]}, {"_id": 0})
    
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found"
        )
    
    return {
        "balance": wallet["balance"],
        "locked_balance": wallet["locked_balance"],
        "available_balance": wallet["balance"] - wallet["locked_balance"]
    }

@router.post("/deposit")
@rate_limit(max_calls=10, time_window=3600)  # 10 deposits per hour
async def request_deposit(deposit_req: DepositRequest, request: Request):
    """Request a deposit"""
    user = await get_current_user(request)
    db = get_database()
    
    if deposit_req.amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Amount must be greater than 0"
        )
    
    # Create deposit request
    deposit_data = {
        "user_id": user["id"],
        "amount": deposit_req.amount,
        "payment_method": deposit_req.payment_method,
        "payment_proof": deposit_req.payment_proof,
        "status": TransactionStatus.PENDING,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.deposit_requests.insert_one(deposit_data)
    
    # Create transaction
    transaction = {
        "user_id": user["id"],
        "type": TransactionType.DEPOSIT,
        "amount": deposit_req.amount,
        "status": TransactionStatus.PENDING,
        "description": f"Deposit request via {deposit_req.payment_method}",
        "metadata": {"payment_method": deposit_req.payment_method},
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.transactions.insert_one(transaction)
    
    await log_audit(db, user["id"], "DEPOSIT_REQUESTED", {"amount": deposit_req.amount}, request)
    
    return {
        "success": True,
        "message": "Deposit request submitted. Waiting for admin approval."
    }

@router.post("/withdraw")
@rate_limit(max_calls=10, time_window=3600)  # 10 withdrawals per hour
async def request_withdrawal(withdrawal_req: WithdrawalRequest, request: Request):
    """Request a withdrawal"""
    user = await get_current_user(request)
    db = get_database()
    
    if withdrawal_req.amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Amount must be greater than 0"
        )
    
    # Check balance
    wallet = await db.wallets.find_one({"user_id": user["id"]}, {"_id": 0})
    available_balance = wallet["balance"] - wallet["locked_balance"]
    
    if available_balance < withdrawal_req.amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient available balance"
        )
    
    # Lock the amount
    await db.wallets.update_one(
        {"user_id": user["id"]},
        {"$inc": {"locked_balance": withdrawal_req.amount}}
    )
    
    # Create withdrawal request
    withdrawal_data = {
        "user_id": user["id"],
        "amount": withdrawal_req.amount,
        "withdrawal_method": withdrawal_req.withdrawal_method,
        "withdrawal_address": withdrawal_req.withdrawal_address,
        "status": TransactionStatus.PENDING,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.withdrawal_requests.insert_one(withdrawal_data)
    
    # Create transaction
    transaction = {
        "user_id": user["id"],
        "type": TransactionType.WITHDRAWAL,
        "amount": withdrawal_req.amount,
        "status": TransactionStatus.PENDING,
        "description": f"Withdrawal request via {withdrawal_req.withdrawal_method}",
        "metadata": {
            "withdrawal_method": withdrawal_req.withdrawal_method,
            "withdrawal_address": withdrawal_req.withdrawal_address
        },
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.transactions.insert_one(transaction)
    
    await log_audit(db, user["id"], "WITHDRAWAL_REQUESTED", {"amount": withdrawal_req.amount}, request)
    
    return {
        "success": True,
        "message": "Withdrawal request submitted. Waiting for admin approval."
    }

@router.get("/transactions", response_model=List[Transaction])
async def get_transactions(
    request: Request,
    type: str = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    """Get transaction history"""
    user = await get_current_user(request)
    db = get_database()
    
    query = {"user_id": user["id"]}
    if type:
        query["type"] = type
    
    transactions = await db.transactions.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    
    # Convert datetime strings
    for tx in transactions:
        if isinstance(tx["created_at"], str):
            tx["created_at"] = datetime.fromisoformat(tx["created_at"])
    
    return transactions
