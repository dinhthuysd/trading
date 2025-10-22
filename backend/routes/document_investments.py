from fastapi import APIRouter, HTTPException, status, Request
from models import DocumentInvestment, DocumentInvestmentRequest, DocumentStatus, TransactionType, TransactionStatus
from middleware import get_current_user, rate_limit, log_audit
from database import get_database
from datetime import datetime, timezone
from typing import List

router = APIRouter(prefix="/document-investments", tags=["Document Investments"])

@router.post("/invest")
@rate_limit(max_calls=20, time_window=3600)
async def invest_in_document(investment_req: DocumentInvestmentRequest, request: Request):
    """Invest in a document to earn revenue share"""
    user = await get_current_user(request)
    db = get_database()
    
    # Get document
    document = await db.documents.find_one({"id": investment_req.document_id}, {"_id": 0})
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    if document["status"] != DocumentStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only invest in approved documents"
        )
    
    # Check balance
    wallet = await db.wallets.find_one({"user_id": user["id"]}, {"_id": 0})
    available_balance = wallet["balance"] - wallet["locked_balance"]
    
    if available_balance < investment_req.amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient available balance"
        )
    
    # Calculate share percentage (simple: amount / document price)
    # In real scenario, this would be more complex
    share_percentage = min((investment_req.amount / document["price"]) * 10, 50)  # Max 50% share
    
    # Lock amount in wallet
    await db.wallets.update_one(
        {"user_id": user["id"]},
        {"$inc": {"locked_balance": investment_req.amount}}
    )
    
    # Create investment
    investment = DocumentInvestment(
        user_id=user["id"],
        document_id=investment_req.document_id,
        amount=investment_req.amount,
        share_percentage=share_percentage
    )
    
    investment_dict = investment.model_dump()
    investment_dict["created_at"] = investment_dict["created_at"].isoformat()
    
    await db.document_investments.insert_one(investment_dict)
    
    # Create transaction
    transaction = {
        "user_id": user["id"],
        "type": TransactionType.INVESTMENT,
        "amount": investment_req.amount,
        "status": TransactionStatus.COMPLETED,
        "description": f"Invested in document: {document['title']}",
        "metadata": {"document_id": investment_req.document_id, "share_percentage": share_percentage},
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.transactions.insert_one(transaction)
    
    await log_audit(db, user["id"], "DOCUMENT_INVESTMENT", {"amount": investment_req.amount, "document_id": investment_req.document_id}, request)
    
    return {
        "success": True,
        "message": f"Successfully invested {investment_req.amount} in document",
        "share_percentage": share_percentage
    }

@router.get("/portfolio", response_model=List[DocumentInvestment])
async def get_document_investment_portfolio(request: Request):
    """Get user's document investment portfolio"""
    user = await get_current_user(request)
    db = get_database()
    
    investments = await db.document_investments.find(
        {"user_id": user["id"]},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    # Convert datetime strings and enrich with document info
    for inv in investments:
        if isinstance(inv["created_at"], str):
            inv["created_at"] = datetime.fromisoformat(inv["created_at"])
        
        # Get document info
        document = await db.documents.find_one({"id": inv["document_id"]}, {"_id": 0})
        if document:
            inv["document_title"] = document["title"]
            inv["document_revenue"] = document.get("revenue", 0)
    
    return investments

@router.get("/returns")
async def get_document_investment_returns(request: Request):
    """Get total document investment returns"""
    user = await get_current_user(request)
    db = get_database()
    
    investments = await db.document_investments.find(
        {"user_id": user["id"]},
        {"_id": 0}
    ).to_list(1000)
    
    total_invested = sum(inv["amount"] for inv in investments)
    total_earned = sum(inv.get("revenue_earned", 0) for inv in investments)
    
    return {
        "total_invested": total_invested,
        "total_earned": total_earned,
        "total_investments": len(investments)
    }
