from fastapi import APIRouter, HTTPException, status, Request, Query
from models import CryptoWallet, CryptoDepositRequest, CryptoWithdrawalRequest, CryptoType, TransactionType, TransactionStatus
from middleware import get_current_user, rate_limit, log_audit
from database import get_database
from datetime import datetime, timezone
from typing import List
import secrets
import hashlib

router = APIRouter(prefix="/crypto", tags=["Cryptocurrency"])

# Mock functions (replace with real integration later)
def generate_crypto_address(crypto_type: CryptoType) -> str:
    """Generate a mock crypto address"""
    prefix = "1" if crypto_type == CryptoType.BITCOIN else "0x"
    random_hash = hashlib.sha256(secrets.token_bytes(32)).hexdigest()
    return f"{prefix}{random_hash[:40]}"

def verify_crypto_transaction(tx_hash: str, crypto_type: CryptoType) -> bool:
    """Mock verification - always returns True"""
    # TODO: Integrate with Coinbase API or Web3
    return True

def get_crypto_balance_from_blockchain(address: str, crypto_type: CryptoType) -> float:
    """Mock balance check"""
    # TODO: Integrate with blockchain API
    return 0.0

def send_crypto_transaction(to_address: str, amount: float, crypto_type: CryptoType) -> str:
    """Mock send transaction"""
    # TODO: Integrate with Coinbase API or Web3
    return hashlib.sha256(secrets.token_bytes(32)).hexdigest()

def get_crypto_rate(crypto_type: CryptoType) -> float:
    """Mock crypto to USD rate"""
    # TODO: Integrate with real price API
    rates = {
        CryptoType.BITCOIN: 45000.0,
        CryptoType.ETHEREUM: 3000.0
    }
    return rates.get(crypto_type, 0.0)

@router.post("/wallets/create")
async def create_crypto_wallet(crypto_type: CryptoType, request: Request):
    """Create a crypto wallet"""
    user = await get_current_user(request)
    db = get_database()
    
    # Check if wallet already exists
    existing_wallet = await db.crypto_wallets.find_one({
        "user_id": user["id"],
        "crypto_type": crypto_type
    })
    
    if existing_wallet:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{crypto_type} wallet already exists"
        )
    
    # Generate address
    address = generate_crypto_address(crypto_type)
    
    # Create wallet
    wallet = {
        "user_id": user["id"],
        "crypto_type": crypto_type,
        "address": address,
        "balance": 0.0,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.crypto_wallets.insert_one(wallet)
    
    await log_audit(db, user["id"], "CRYPTO_WALLET_CREATED", {"crypto_type": crypto_type, "address": address}, request)
    
    return {
        "success": True,
        "wallet": {
            "crypto_type": crypto_type,
            "address": address,
            "balance": 0.0
        }
    }

@router.get("/wallets", response_model=List[CryptoWallet])
async def get_crypto_wallets(request: Request):
    """Get all crypto wallets"""
    user = await get_current_user(request)
    db = get_database()
    
    wallets = await db.crypto_wallets.find(
        {"user_id": user["id"]},
        {"_id": 0}
    ).to_list(100)
    
    # Convert datetime strings
    for wallet in wallets:
        if isinstance(wallet["created_at"], str):
            wallet["created_at"] = datetime.fromisoformat(wallet["created_at"])
    
    return wallets

@router.get("/wallets/{wallet_id}/balance")
async def get_crypto_balance(wallet_id: str, request: Request):
    """Get crypto wallet balance"""
    user = await get_current_user(request)
    db = get_database()
    
    wallet = await db.crypto_wallets.find_one(
        {"id": wallet_id, "user_id": user["id"]},
        {"_id": 0}
    )
    
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not found"
        )
    
    # Get balance from blockchain (mock)
    blockchain_balance = get_crypto_balance_from_blockchain(wallet["address"], wallet["crypto_type"])
    
    return {
        "crypto_type": wallet["crypto_type"],
        "address": wallet["address"],
        "balance": wallet["balance"],
        "blockchain_balance": blockchain_balance
    }

@router.post("/deposit")
@rate_limit(max_calls=10, time_window=3600)
async def crypto_deposit(deposit_req: CryptoDepositRequest, request: Request):
    """Process crypto deposit"""
    user = await get_current_user(request)
    db = get_database()
    
    # Verify transaction on blockchain (mock)
    if not verify_crypto_transaction(deposit_req.tx_hash, deposit_req.crypto_type):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid transaction hash"
        )
    
    # Get wallet
    wallet = await db.crypto_wallets.find_one({
        "user_id": user["id"],
        "crypto_type": deposit_req.crypto_type
    }, {"_id": 0})
    
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Crypto wallet not found. Create one first."
        )
    
    # Update balance
    await db.crypto_wallets.update_one(
        {"user_id": user["id"], "crypto_type": deposit_req.crypto_type},
        {"$inc": {"balance": deposit_req.amount}}
    )
    
    # Convert to internal currency and add to main wallet
    rate = get_crypto_rate(deposit_req.crypto_type)
    usd_amount = deposit_req.amount * rate
    
    await db.wallets.update_one(
        {"user_id": user["id"]},
        {"$inc": {"balance": usd_amount}}
    )
    
    # Create transaction
    transaction = {
        "user_id": user["id"],
        "type": TransactionType.DEPOSIT,
        "amount": usd_amount,
        "status": TransactionStatus.COMPLETED,
        "description": f"Crypto deposit: {deposit_req.amount} {deposit_req.crypto_type}",
        "metadata": {
            "crypto_type": deposit_req.crypto_type,
            "crypto_amount": deposit_req.amount,
            "tx_hash": deposit_req.tx_hash,
            "rate": rate
        },
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.transactions.insert_one(transaction)
    
    await log_audit(db, user["id"], "CRYPTO_DEPOSIT", {"amount": deposit_req.amount, "crypto_type": deposit_req.crypto_type}, request)
    
    return {
        "success": True,
        "message": f"Deposited {deposit_req.amount} {deposit_req.crypto_type} (${usd_amount:.2f})"
    }

@router.post("/withdraw")
@rate_limit(max_calls=10, time_window=3600)
async def crypto_withdraw(withdrawal_req: CryptoWithdrawalRequest, request: Request):
    """Withdraw crypto"""
    user = await get_current_user(request)
    db = get_database()
    
    # Get wallet
    wallet = await db.crypto_wallets.find_one({
        "user_id": user["id"],
        "crypto_type": withdrawal_req.crypto_type
    }, {"_id": 0})
    
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Crypto wallet not found"
        )
    
    if wallet["balance"] < withdrawal_req.amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient crypto balance"
        )
    
    # Send transaction (mock)
    tx_hash = send_crypto_transaction(withdrawal_req.to_address, withdrawal_req.amount, withdrawal_req.crypto_type)
    
    # Update balance
    await db.crypto_wallets.update_one(
        {"user_id": user["id"], "crypto_type": withdrawal_req.crypto_type},
        {"$inc": {"balance": -withdrawal_req.amount}}
    )
    
    # Create transaction
    rate = get_crypto_rate(withdrawal_req.crypto_type)
    usd_amount = withdrawal_req.amount * rate
    
    transaction = {
        "user_id": user["id"],
        "type": TransactionType.WITHDRAWAL,
        "amount": usd_amount,
        "status": TransactionStatus.COMPLETED,
        "description": f"Crypto withdrawal: {withdrawal_req.amount} {withdrawal_req.crypto_type}",
        "metadata": {
            "crypto_type": withdrawal_req.crypto_type,
            "crypto_amount": withdrawal_req.amount,
            "to_address": withdrawal_req.to_address,
            "tx_hash": tx_hash,
            "rate": rate
        },
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.transactions.insert_one(transaction)
    
    await log_audit(db, user["id"], "CRYPTO_WITHDRAWAL", {"amount": withdrawal_req.amount, "crypto_type": withdrawal_req.crypto_type}, request)
    
    return {
        "success": True,
        "message": f"Withdrew {withdrawal_req.amount} {withdrawal_req.crypto_type}",
        "tx_hash": tx_hash
    }

@router.get("/transactions")
async def get_crypto_transactions(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    """Get crypto transaction history"""
    user = await get_current_user(request)
    db = get_database()
    
    transactions = await db.transactions.find(
        {
            "user_id": user["id"],
            "metadata.crypto_type": {"$exists": True}
        },
        {"_id": 0}
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    
    # Convert datetime strings
    for tx in transactions:
        if isinstance(tx["created_at"], str):
            tx["created_at"] = datetime.fromisoformat(tx["created_at"])
    
    return transactions

@router.get("/rates")
async def get_crypto_rates():
    """Get current crypto rates"""
    return {
        "bitcoin": get_crypto_rate(CryptoType.BITCOIN),
        "ethereum": get_crypto_rate(CryptoType.ETHEREUM)
    }
