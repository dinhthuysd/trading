from fastapi import APIRouter, HTTPException, status, Request, Query
from models import StakingPosition, StakingRequest, TransactionType, TransactionStatus
from middleware import get_current_user, rate_limit, log_audit
from database import get_database
from config import settings
from datetime import datetime, timedelta, timezone
from typing import List

router = APIRouter(prefix="/staking", tags=["Staking"])

@router.get("/plans")
async def get_staking_plans():
    """Get available staking plans"""
    return {
        "plans": [
            {
                "name": "basic",
                "min_amount": settings.STAKING_PLANS["basic"]["min_amount"],
                "apy": settings.STAKING_PLANS["basic"]["apy"],
                "lock_days": settings.STAKING_PLANS["basic"]["lock_days"],
                "description": "Basic staking plan with 5% APY for 30 days"
            },
            {
                "name": "premium",
                "min_amount": settings.STAKING_PLANS["premium"]["min_amount"],
                "apy": settings.STAKING_PLANS["premium"]["apy"],
                "lock_days": settings.STAKING_PLANS["premium"]["lock_days"],
                "description": "Premium staking plan with 10% APY for 90 days"
            },
            {
                "name": "vip",
                "min_amount": settings.STAKING_PLANS["vip"]["min_amount"],
                "apy": settings.STAKING_PLANS["vip"]["apy"],
                "lock_days": settings.STAKING_PLANS["vip"]["lock_days"],
                "description": "VIP staking plan with 15% APY for 180 days"
            }
        ]
    }

@router.post("/stake")
@rate_limit(max_calls=20, time_window=3600)
async def stake_coins(stake_req: StakingRequest, request: Request):
    """Stake coins"""
    user = await get_current_user(request)
    db = get_database()
    
    # Validate plan
    if stake_req.plan not in settings.STAKING_PLANS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid staking plan"
        )
    
    plan_config = settings.STAKING_PLANS[stake_req.plan]
    
    # Validate amount
    if stake_req.amount < plan_config["min_amount"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Minimum amount for {stake_req.plan} plan is {plan_config['min_amount']}"
        )
    
    # Check balance
    wallet = await db.wallets.find_one({"user_id": user["id"]}, {"_id": 0})
    available_balance = wallet["balance"] - wallet["locked_balance"]
    
    if available_balance < stake_req.amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient available balance"
        )
    
    # Lock amount in wallet
    await db.wallets.update_one(
        {"user_id": user["id"]},
        {"$inc": {"locked_balance": stake_req.amount}}
    )
    
    # Create staking position
    locked_until = datetime.now(timezone.utc) + timedelta(days=plan_config["lock_days"])
    
    position = StakingPosition(
        user_id=user["id"],
        plan=stake_req.plan,
        amount=stake_req.amount,
        apy=plan_config["apy"],
        locked_until=locked_until
    )
    
    position_dict = position.model_dump()
    position_dict["locked_until"] = position_dict["locked_until"].isoformat()
    position_dict["created_at"] = position_dict["created_at"].isoformat()
    
    await db.staking_positions.insert_one(position_dict)
    
    # Create transaction
    transaction = {
        "user_id": user["id"],
        "type": TransactionType.STAKING,
        "amount": stake_req.amount,
        "status": TransactionStatus.COMPLETED,
        "description": f"Staked {stake_req.amount} in {stake_req.plan} plan",
        "metadata": {"plan": stake_req.plan, "position_id": position.id},
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.transactions.insert_one(transaction)
    
    await log_audit(db, user["id"], "COINS_STAKED", {"amount": stake_req.amount, "plan": stake_req.plan}, request)
    
    return {
        "success": True,
        "message": f"Successfully staked {stake_req.amount} coins",
        "position": position_dict
    }

@router.post("/unstake/{position_id}")
async def unstake_coins(position_id: str, request: Request):
    """Unstake coins"""
    user = await get_current_user(request)
    db = get_database()
    
    # Get position
    position = await db.staking_positions.find_one(
        {"id": position_id, "user_id": user["id"]},
        {"_id": 0}
    )
    
    if not position:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staking position not found"
        )
    
    if position["status"] != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Position is not active"
        )
    
    # Check if lock period has ended
    locked_until = datetime.fromisoformat(position["locked_until"]) if isinstance(position["locked_until"], str) else position["locked_until"]
    current_time = datetime.now(timezone.utc)
    
    if current_time < locked_until:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Coins are locked until {locked_until.isoformat()}"
        )
    
    # Calculate rewards
    days_staked = (current_time - (datetime.fromisoformat(position["created_at"]) if isinstance(position["created_at"], str) else position["created_at"])).days
    annual_reward = position["amount"] * (position["apy"] / 100)
    daily_reward = annual_reward / 365
    total_reward = daily_reward * days_staked
    
    # Unlock amount and add rewards
    total_return = position["amount"] + total_reward
    
    await db.wallets.update_one(
        {"user_id": user["id"]},
        {
            "$inc": {
                "balance": total_reward,
                "locked_balance": -position["amount"]
            }
        }
    )
    
    # Update position
    await db.staking_positions.update_one(
        {"id": position_id},
        {
            "$set": {
                "status": "completed",
                "rewards_earned": total_reward
            }
        }
    )
    
    # Create transactions
    unstake_tx = {
        "user_id": user["id"],
        "type": TransactionType.UNSTAKING,
        "amount": position["amount"],
        "status": TransactionStatus.COMPLETED,
        "description": f"Unstaked from {position['plan']} plan",
        "metadata": {"position_id": position_id},
        "created_at": current_time.isoformat()
    }
    
    reward_tx = {
        "user_id": user["id"],
        "type": TransactionType.REWARD,
        "amount": total_reward,
        "status": TransactionStatus.COMPLETED,
        "description": f"Staking rewards from {position['plan']} plan",
        "metadata": {"position_id": position_id},
        "created_at": current_time.isoformat()
    }
    
    await db.transactions.insert_one(unstake_tx)
    await db.transactions.insert_one(reward_tx)
    
    await log_audit(db, user["id"], "COINS_UNSTAKED", {"amount": position["amount"], "reward": total_reward}, request)
    
    return {
        "success": True,
        "message": f"Successfully unstaked {position['amount']} coins with {total_reward:.2f} rewards",
        "principal": position["amount"],
        "rewards": total_reward,
        "total": total_return
    }

@router.get("/positions", response_model=List[StakingPosition])
async def get_staking_positions(request: Request):
    """Get user's staking positions"""
    user = await get_current_user(request)
    db = get_database()
    
    positions = await db.staking_positions.find(
        {"user_id": user["id"]},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    # Convert datetime strings
    for pos in positions:
        if isinstance(pos["created_at"], str):
            pos["created_at"] = datetime.fromisoformat(pos["created_at"])
        if isinstance(pos["locked_until"], str):
            pos["locked_until"] = datetime.fromisoformat(pos["locked_until"])
    
    return positions

@router.get("/rewards")
async def get_staking_rewards(request: Request):
    """Get total staking rewards"""
    user = await get_current_user(request)
    db = get_database()
    
    # Get all completed positions
    positions = await db.staking_positions.find(
        {"user_id": user["id"]},
        {"_id": 0}
    ).to_list(1000)
    
    total_earned = sum(pos.get("rewards_earned", 0) for pos in positions)
    active_positions = [pos for pos in positions if pos["status"] == "active"]
    
    # Calculate pending rewards
    pending_rewards = 0
    for pos in active_positions:
        created_at = datetime.fromisoformat(pos["created_at"]) if isinstance(pos["created_at"], str) else pos["created_at"]
        days_staked = (datetime.now(timezone.utc) - created_at).days
        annual_reward = pos["amount"] * (pos["apy"] / 100)
        daily_reward = annual_reward / 365
        pending_rewards += daily_reward * days_staked
    
    return {
        "total_earned": total_earned,
        "pending_rewards": pending_rewards,
        "active_positions": len(active_positions)
    }
