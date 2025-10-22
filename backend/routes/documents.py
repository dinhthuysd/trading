from fastapi import APIRouter, HTTPException, status, Request, UploadFile, File, Query
from models import DocumentCreate, Document, DocumentStatus, TransactionType, TransactionStatus
from middleware import get_current_user, get_optional_user, rate_limit, log_audit
from database import get_database, get_gridfs
from datetime import datetime, timezone
from typing import List, Optional
from fastapi.responses import StreamingResponse
import io

router = APIRouter(prefix="/documents", tags=["Documents"])

@router.post("", response_model=Document, status_code=status.HTTP_201_CREATED)
@rate_limit(max_calls=20, time_window=3600)  # 20 uploads per hour
async def upload_document(
    request: Request,
    title: str,
    description: str,
    category: str,
    price: float,
    tags: str = "",
    file: UploadFile = File(...)
):
    """Upload a document for sale"""
    user = await get_current_user(request)
    db = get_database()
    fs = get_gridfs()
    
    # Read file
    file_content = await file.read()
    file_size = len(file_content)
    
    # Upload to GridFS
    file_id = await fs.upload_from_stream(
        file.filename,
        file_content,
        metadata={
            "user_id": user["id"],
            "type": "document",
            "category": category
        }
    )
    
    # Create document
    doc = Document(
        title=title,
        description=description,
        category=category,
        price=price,
        seller_id=user["id"],
        file_id=str(file_id),
        file_name=file.filename,
        file_size=file_size,
        tags=tags.split(",") if tags else []
    )
    
    doc_dict = doc.model_dump()
    doc_dict["created_at"] = doc_dict["created_at"].isoformat()
    doc_dict["updated_at"] = doc_dict["updated_at"].isoformat()
    
    await db.documents.insert_one(doc_dict)
    
    await log_audit(db, user["id"], "DOCUMENT_UPLOADED", {"document_id": doc.id, "title": title}, request)
    
    return doc

@router.get("", response_model=List[Document])
async def get_documents(
    request: Request,
    category: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    """Get list of documents"""
    db = get_database()
    user = await get_optional_user(request)
    
    # Build query
    query = {}
    
    # Only show approved documents to non-sellers
    if not user or user.get("role") not in ["admin", "seller"]:
        query["status"] = DocumentStatus.APPROVED
    elif status:
        query["status"] = status
    
    if category:
        query["category"] = category
    
    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
            {"tags": {"$in": [search]}}
        ]
    
    documents = await db.documents.find(query, {"_id": 0}).skip(skip).limit(limit).to_list(limit)
    
    # Convert datetime strings
    for doc in documents:
        if isinstance(doc["created_at"], str):
            doc["created_at"] = datetime.fromisoformat(doc["created_at"])
        if isinstance(doc["updated_at"], str):
            doc["updated_at"] = datetime.fromisoformat(doc["updated_at"])
    
    return documents

@router.get("/{document_id}", response_model=Document)
async def get_document(document_id: str, request: Request):
    """Get document details"""
    db = get_database()
    
    document = await db.documents.find_one({"id": document_id}, {"_id": 0})
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Convert datetime strings
    if isinstance(document["created_at"], str):
        document["created_at"] = datetime.fromisoformat(document["created_at"])
    if isinstance(document["updated_at"], str):
        document["updated_at"] = datetime.fromisoformat(document["updated_at"])
    
    return document

@router.get("/{document_id}/download")
async def download_document(document_id: str, request: Request):
    """Download a purchased document"""
    user = await get_current_user(request)
    db = get_database()
    fs = get_gridfs()
    
    # Get document
    document = await db.documents.find_one({"id": document_id}, {"_id": 0})
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Check if user is seller or has purchased
    if document["seller_id"] != user["id"]:
        purchase = await db.transactions.find_one({
            "user_id": user["id"],
            "type": TransactionType.PURCHASE,
            "metadata.document_id": document_id,
            "status": TransactionStatus.COMPLETED
        })
        
        if not purchase:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You must purchase this document first"
            )
    
    # Download from GridFS
    from bson import ObjectId
    file_stream = await fs.open_download_stream(ObjectId(document["file_id"]))
    file_content = await file_stream.read()
    
    await log_audit(db, user["id"], "DOCUMENT_DOWNLOADED", {"document_id": document_id}, request)
    
    return StreamingResponse(
        io.BytesIO(file_content),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={document['file_name']}"}
    )

@router.post("/{document_id}/purchase")
async def purchase_document(document_id: str, request: Request):
    """Purchase a document"""
    user = await get_current_user(request)
    db = get_database()
    
    # Get document
    document = await db.documents.find_one({"id": document_id}, {"_id": 0})
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    if document["status"] != DocumentStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document not available for purchase"
        )
    
    # Check if already purchased
    existing_purchase = await db.transactions.find_one({
        "user_id": user["id"],
        "type": TransactionType.PURCHASE,
        "metadata.document_id": document_id,
        "status": TransactionStatus.COMPLETED
    })
    
    if existing_purchase:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already purchased this document"
        )
    
    # Get wallet
    wallet = await db.wallets.find_one({"user_id": user["id"]}, {"_id": 0})
    
    if wallet["balance"] < document["price"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient balance"
        )
    
    # Deduct from buyer
    await db.wallets.update_one(
        {"user_id": user["id"]},
        {"$inc": {"balance": -document["price"]}}
    )
    
    # Add to seller
    await db.wallets.update_one(
        {"user_id": document["seller_id"]},
        {"$inc": {"balance": document["price"]}}
    )
    
    # Create purchase transaction
    transaction = {
        "user_id": user["id"],
        "type": TransactionType.PURCHASE,
        "amount": document["price"],
        "status": TransactionStatus.COMPLETED,
        "description": f"Purchased document: {document['title']}",
        "metadata": {"document_id": document_id},
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.transactions.insert_one(transaction)
    
    # Create sale transaction for seller
    sale_transaction = {
        "user_id": document["seller_id"],
        "type": TransactionType.SALE,
        "amount": document["price"],
        "status": TransactionStatus.COMPLETED,
        "description": f"Sold document: {document['title']}",
        "metadata": {"document_id": document_id, "buyer_id": user["id"]},
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.transactions.insert_one(sale_transaction)
    
    # Update document stats
    await db.documents.update_one(
        {"id": document_id},
        {"$inc": {"downloads": 1, "revenue": document["price"]}}
    )
    
    # Distribute to investors if any
    investments = await db.document_investments.find({"document_id": document_id}).to_list(100)
    for investment in investments:
        investor_share = document["price"] * (investment["share_percentage"] / 100)
        
        await db.wallets.update_one(
            {"user_id": investment["user_id"]},
            {"$inc": {"balance": investor_share}}
        )
        
        await db.document_investments.update_one(
            {"id": investment["id"]},
            {"$inc": {"revenue_earned": investor_share}}
        )
        
        # Create reward transaction
        reward_tx = {
            "user_id": investment["user_id"],
            "type": TransactionType.REWARD,
            "amount": investor_share,
            "status": TransactionStatus.COMPLETED,
            "description": f"Investment return from document: {document['title']}",
            "metadata": {"document_id": document_id},
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.transactions.insert_one(reward_tx)
    
    await log_audit(db, user["id"], "DOCUMENT_PURCHASED", {"document_id": document_id, "price": document["price"]}, request)
    
    return {"success": True, "message": "Document purchased successfully"}

@router.delete("/{document_id}")
async def delete_document(document_id: str, request: Request):
    """Delete a document"""
    user = await get_current_user(request)
    db = get_database()
    fs = get_gridfs()
    
    # Get document
    document = await db.documents.find_one({"id": document_id}, {"_id": 0})
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Check ownership or admin
    if document["seller_id"] != user["id"] and user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this document"
        )
    
    # Delete from GridFS
    from bson import ObjectId
    await fs.delete(ObjectId(document["file_id"]))
    
    # Delete document
    await db.documents.delete_one({"id": document_id})
    
    await log_audit(db, user["id"], "DOCUMENT_DELETED", {"document_id": document_id}, request)
    
    return {"success": True, "message": "Document deleted successfully"}
