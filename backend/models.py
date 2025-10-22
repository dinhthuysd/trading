from pydantic import BaseModel, Field, EmailStr, ConfigDict, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from enum import Enum
import uuid

# Enums
class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"
    SELLER = "seller"

class KYCStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"

class DocumentStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class TransactionType(str, Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    PURCHASE = "purchase"
    SALE = "sale"
    STAKING = "staking"
    UNSTAKING = "unstaking"
    INVESTMENT = "investment"
    REWARD = "reward"

class TransactionStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class CryptoType(str, Enum):
    BITCOIN = "bitcoin"
    ETHEREUM = "ethereum"

# User Models
class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    phone: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str
    totp_code: Optional[str] = None

class User(UserBase):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: UserRole = UserRole.USER
    is_active: bool = True
    is_2fa_enabled: bool = False
    kyc_status: KYCStatus = KYCStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserProfile(BaseModel):
    id: str
    email: str
    username: str
    full_name: Optional[str]
    phone: Optional[str]
    role: str
    kyc_status: str
    is_2fa_enabled: bool
    created_at: datetime

# Auth Models
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    user_id: str
    email: str
    role: str

class TwoFactorSetup(BaseModel):
    secret: str
    qr_code: str

class TwoFactorVerify(BaseModel):
    totp_code: str

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordReset(BaseModel):
    token: str
    new_password: str

# Session Models
class Session(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    session_token: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Document Models
class DocumentCreate(BaseModel):
    title: str
    description: str
    category: str
    price: float
    tags: List[str] = []

class Document(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    category: str
    price: float
    seller_id: str
    file_id: str  # GridFS file ID
    file_name: str
    file_size: int
    tags: List[str] = []
    status: DocumentStatus = DocumentStatus.PENDING
    downloads: int = 0
    revenue: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Wallet Models
class Wallet(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    balance: float = 0.0
    locked_balance: float = 0.0  # Locked in staking/investments
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class DepositRequest(BaseModel):
    amount: float
    payment_method: str
    payment_proof: Optional[str] = None

class WithdrawalRequest(BaseModel):
    amount: float
    withdrawal_method: str
    withdrawal_address: str

# Transaction Models
class Transaction(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    type: TransactionType
    amount: float
    status: TransactionStatus = TransactionStatus.PENDING
    description: str
    metadata: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Crypto Wallet Models
class CryptoWallet(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    crypto_type: CryptoType
    address: str
    balance: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CryptoDepositRequest(BaseModel):
    crypto_type: CryptoType
    amount: float
    tx_hash: str

class CryptoWithdrawalRequest(BaseModel):
    crypto_type: CryptoType
    amount: float
    to_address: str

# Staking Models
class StakingPosition(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    plan: str  # basic, premium, vip
    amount: float
    apy: float
    locked_until: datetime
    rewards_earned: float = 0.0
    status: str = "active"  # active, completed
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StakingRequest(BaseModel):
    plan: str
    amount: float

# Investment Models
class InvestmentPosition(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    package: str  # starter, growth, premium
    amount: float
    expected_return: float
    expires_at: datetime
    returns_earned: float = 0.0
    status: str = "active"  # active, completed
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class InvestmentRequest(BaseModel):
    package: str

# Document Investment Models
class DocumentInvestment(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    document_id: str
    amount: float
    share_percentage: float
    revenue_earned: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class DocumentInvestmentRequest(BaseModel):
    document_id: str
    amount: float

# KYC Models
class KYCSubmission(BaseModel):
    id_type: str  # passport, id_card, driver_license
    id_number: str
    id_front_image: str
    id_back_image: Optional[str] = None
    selfie_image: str
    address_proof: Optional[str] = None

# Audit Log Models
class AuditLog(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    action: str
    details: Dict[str, Any] = {}
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Response Models
class SuccessResponse(BaseModel):
    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None

class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    details: Optional[Dict[str, Any]] = None
