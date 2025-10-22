from fastapi import APIRouter, HTTPException, status, Request, Query
from models import InvestmentPosition, InvestmentRequest, DocumentInvestment, DocumentInvestmentRequest, TransactionType, TransactionStatus
from middleware import get_current_user, rate_limit, log_audit
from database import get_database
from config import settings
from datetime import datetime, timedelta, timezone
from typing import List

router = APIRouter(prefix="/investments", tags=["Investments"])

@router.get("/packages")
async def get_investment_packages():
    """Get available investment packages"""
    return {
        "packages": [
            {
                "name": "starter",
                "price": settings.INVESTMENT_PACKAGES["starter"]["price"],
                "expected_return": settings.INVESTMENT_PACKAGES["starter"]["expected_return"],
                "duration_days": settings.INVESTMENT_PACKAGES["starter"]["duration_days"],
                "description": "Starter investment package with 8% expected return in 60 days"
            },
            {
                "name": "growth",
                "price": settings.INVESTMENT_PACKAGES["growth"]["price"],
                "expected_return": settings.INVESTMENT_PACKAGES["growth"]["expected_return"],
                "duration_days": settings.INVESTMENT_PACKAGES["growth"]["duration_days"],
                "description": "Growth investment package with 12% expected return in 90 days"
            },
            {
                "name": "premium",
                "price": settings.INVESTMENT_PACKAGES["premium"]["price"],
                "expected_return": settings.INVESTMENT_PACKAGES["premium"]["expected_return"],
                "duration_days": settings.INVESTMENT_PACKAGES["premium"]["duration_days"],
                "description": "Premium investment package with 18% expected return in 180 days"
            }
        ]
    }

@router.post("/purchase")
@rate_limit(max_calls=20, time_window=3600)
async def purchase_investment(investment_req: InvestmentRequest, request: Request):
    """Purchase an investment package"""
    user = await get_current_user(request)
    db = get_database()
    
    # Validate package
    if investment_req.package not in settings.INVESTMENT_PACKAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid investment package"
        )
    
    package_config = settings.INVESTMENT_PACKAGES[investment_req.package]
    
    # Check balance
    wallet = await db.wallets.find_one({"user_id": user["id"]}, {"_id": 0})
    available_balance = wallet["balance"] - wallet["locked_balance"]
    
    if available_balance < package_config["price"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient available balance"
        )
    
    # Lock amount in wallet
    await db.wallets.update_one(
        {"user_id": user["id"]},
        {"$inc": {"locked_balance": package_config["price"]}}
    )
    
    # Create investment position
    expires_at = datetime.now(timezone.utc) + timedelta(days=package_config["duration_days"])
    
    position = InvestmentPosition(
        user_id=user["id"],
        package=investment_req.package,
        amount=package_config["price"],
        expected_return=package_config["expected_return"],
        expires_at=expires_at
    )
    
    position_dict = position.model_dump()
    position_dict["expires_at"] = position_dict["expires_at"].isoformat()
    position_dict["created_at"] = position_dict["created_at"].isoformat()
    
    await db.investment_positions.insert_one(position_dict)
    
    # Create transaction
    transaction = {
        "user_id": user["id"],
        "type": TransactionType.INVESTMENT,
        "amount": package_config["price"],
        "status": TransactionStatus.COMPLETED,
        "description": f"Invested in {investment_req.package} package",
        "metadata": {"package": investment_req.package, "position_id": position.id},
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.transactions.insert_one(transaction)
    
    await log_audit(db, user["id"], "INVESTMENT_PURCHASED", {"amount": package_config["price"], "package": investment_req.package}, request)
    
    return {
        "success": True,
        "message": f"Successfully invested in {investment_req.package} package",
        "position": position_dict
    }

@router.get("/portfolio", response_model=List[InvestmentPosition])
async def get_investment_portfolio(request: Request):
    """Get user's investment portfolio"""
    user = await get_current_user(request)
    db = get_database()
    
    positions = await db.investment_positions.find(
        {"user_id": user["id"]},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    # Convert datetime strings and check for matured investments
    current_time = datetime.now(timezone.utc)
    
    for pos in positions:
        if isinstance(pos["created_at"], str):
            pos["created_at"] = datetime.fromisoformat(pos["created_at"])
        if isinstance(pos["expires_at"], str):
            pos["expires_at"] = datetime.fromisoformat(pos["expires_at"])
        
        # Auto-complete matured investments
        if pos["status"] == "active" and current_time >= pos["expires_at"]:
            returns = pos["amount"] * (pos["expected_return"] / 100)
            total_return = pos["amount"] + returns
            
            # Unlock and add returns
            await db.wallets.update_one(
                {"user_id": user["id"]},
                {
                    "$inc": {
                        "balance": returns,
                        "locked_balance": -pos["amount"]
                    }
                }
            )
            
            # Update position
            await db.investment_positions.update_one(
                {"id": pos["id"]},
                {
                    "$set": {
                        "status": "completed",
                        "returns_earned": returns
                    }
                }
            )
            
            # Create reward transaction
            reward_tx = {
                "user_id": user["id"],
                "type": TransactionType.REWARD,
                "amount": returns,
                "status": TransactionStatus.COMPLETED,
                "description": f"Investment returns from {pos['package']} package",
                "metadata": {"position_id": pos["id"]},
                "created_at": current_time.isoformat()
            }
            await db.transactions.insert_one(reward_tx)
            
            pos["status"] = "completed"
            pos["returns_earned"] = returns
    
    return positions

@router.get("/returns")
async def get_investment_returns(request: Request):
    """Get total investment returns"""
    user = await get_current_user(request)
    db = get_database()
    
    positions = await db.investment_positions.find(
        {"user_id": user["id"]},
        {"_id": 0}
    ).to_list(1000)
    
    total_invested = sum(pos["amount"] for pos in positions)
    total_earned = sum(pos.get("returns_earned", 0) for pos in positions)
    active_positions = [pos for pos in positions if pos["status"] == "active"]
    
    # Calculate expected returns from active positions
    expected_returns = sum(
        pos["amount"] * (pos["expected_return"] / 100)
        for pos in active_positions
    )
    
    return {
        "total_invested": total_invested,
        "total_earned": total_earned,
        "expected_returns": expected_returns,
        "active_positions": len(active_positions)
    }
