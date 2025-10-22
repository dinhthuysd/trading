# Cấu trúc Project - Document Exchange Platform

## 📁 Backend Structure

```
/app/backend/
│
├── server.py                    # ⚡ Main FastAPI application
│   ├── FastAPI app initialization
│   ├── API router với prefix /api
│   ├── CORS middleware
│   ├── Startup/Shutdown events
│   └── Health check endpoint
│
├── config.py                    # ⚙️ Configuration & Settings
│   ├── MongoDB settings
│   ├── JWT configuration
│   ├── Staking plans
│   ├── Investment packages
│   └── API keys (crypto)
│
├── database.py                  # 🗄️ Database Connection
│   ├── MongoDB async client
│   ├── GridFS bucket
│   ├── Database indexes
│   └── Connection management
│
├── models.py                    # 📦 Pydantic Models
│   ├── User models
│   ├── Document models
│   ├── Transaction models
│   ├── Wallet models
│   ├── Staking models
│   ├── Investment models
│   └── Enums (UserRole, Status, etc.)
│
├── security.py                  # 🔐 Security Utilities
│   ├── Password hashing (bcrypt)
│   ├── JWT token creation
│   ├── Token verification
│   └── Token generation
│
├── middleware.py                # 🛡️ Middleware & Auth
│   ├── Rate limiting
│   ├── Get current user
│   ├── Require admin
│   └── Audit logging
│
├── routes/
│   ├── __init__.py
│   │
│   ├── auth.py                  # 🔑 Authentication (9 endpoints)
│   │   ├── register()
│   │   ├── login()
│   │   ├── refresh_token()
│   │   ├── setup_2fa()
│   │   ├── verify_2fa()
│   │   ├── disable_2fa()
│   │   ├── google_login()
│   │   ├── create_session_from_google()
│   │   └── logout()
│   │
│   ├── users.py                 # 👤 User Management (4 endpoints)
│   │   ├── get_profile()
│   │   ├── update_profile()
│   │   ├── submit_kyc()
│   │   └── get_kyc_status()
│   │
│   ├── documents.py             # 📄 Documents (6 endpoints)
│   │   ├── upload_document()
│   │   ├── get_documents()
│   │   ├── get_document()
│   │   ├── purchase_document()
│   │   ├── download_document()
│   │   └── delete_document()
│   │
│   ├── wallets.py               # 💰 Wallets (4 endpoints)
│   │   ├── get_balance()
│   │   ├── request_deposit()
│   │   ├── request_withdrawal()
│   │   └── get_transactions()
│   │
│   ├── crypto.py                # ₿ Cryptocurrency (7 endpoints)
│   │   ├── create_crypto_wallet()
│   │   ├── get_crypto_wallets()
│   │   ├── get_crypto_balance()
│   │   ├── crypto_deposit()
│   │   ├── crypto_withdraw()
│   │   ├── get_crypto_transactions()
│   │   └── get_crypto_rates()
│   │
│   ├── staking.py               # 🔒 Staking (5 endpoints)
│   │   ├── get_staking_plans()
│   │   ├── stake_coins()
│   │   ├── unstake_coins()
│   │   ├── get_staking_positions()
│   │   └── get_staking_rewards()
│   │
│   ├── investments.py           # 📈 Investments (4 endpoints)
│   │   ├── get_investment_packages()
│   │   ├── purchase_investment()
│   │   ├── get_investment_portfolio()
│   │   └── get_investment_returns()
│   │
│   ├── document_investments.py  # 📊 Doc Investments (3 endpoints)
│   │   ├── invest_in_document()
│   │   ├── get_document_investment_portfolio()
│   │   └── get_document_investment_returns()
│   │
│   └── admin.py                 # 👨‍💼 Admin Panel (13 endpoints)
│       ├── get_users()
│       ├── get_user_details()
│       ├── verify_kyc()
│       ├── update_user_role()
│       ├── get_all_documents()
│       ├── approve_document()
│       ├── get_all_transactions()
│       ├── get_deposit_requests()
│       ├── process_deposit()
│       ├── get_withdrawal_requests()
│       ├── process_withdrawal()
│       ├── get_analytics()
│       └── get_audit_logs()
│
├── .env                         # 🔧 Environment Variables
│   ├── MONGO_URL
│   ├── DB_NAME
│   ├── JWT_SECRET_KEY
│   ├── CORS_ORIGINS
│   └── CRYPTO_API_KEYS
│
└── requirements.txt             # 📦 Python Dependencies
```

---

## 🗂️ Database Collections

```
MongoDB: document_exchange
│
├── users                        # 👥 User accounts
│   └── Indexes: email, username, created_at
│
├── sessions                     # 🔐 Login sessions
│   └── Indexes: session_token, user_id, expires_at
│
├── documents                    # 📄 Documents for sale
│   └── Indexes: seller_id, category, status, created_at
│
├── wallets                      # 💰 Internal wallets
│   └── Indexes: user_id (unique)
│
├── crypto_wallets               # ₿ Crypto wallets
│   └── Indexes: user_id, crypto_type
│
├── transactions                 # 💸 All transactions
│   └── Indexes: user_id, type, created_at
│
├── staking_positions            # 🔒 Staking positions
│   └── Indexes: user_id, status
│
├── investment_positions         # 📈 Investment positions
│   └── Indexes: user_id, status
│
├── document_investments         # 📊 Document investments
│   └── Indexes: user_id, document_id
│
├── kyc_submissions              # 🆔 KYC documents
│   └── Indexes: user_id, status
│
├── deposit_requests             # ⬇️ Deposit requests
│   └── Indexes: user_id, status
│
├── withdrawal_requests          # ⬆️ Withdrawal requests
│   └── Indexes: user_id, status
│
└── audit_logs                   # 📝 Audit trail
    └── Indexes: user_id, action, timestamp
```

---

## 📊 Data Flow

### 1. Authentication Flow
```
User → POST /auth/register
     → Create user in DB
     → Create wallet
     → Return JWT tokens

User → POST /auth/login (with 2FA)
     → Verify credentials
     → Verify TOTP code
     → Return JWT tokens
     → Create session

User → GET /any-protected-route
     → middleware.get_current_user()
     → Verify JWT or session_token
     → Return user data
```

### 2. Document Purchase Flow
```
User → POST /documents/{id}/purchase
     → Check user balance
     → Check document status
     → Deduct from buyer wallet
     → Add to seller wallet
     → Distribute to investors (if any)
     → Create transactions
     → Update document stats
     → Log audit
```

### 3. Staking Flow
```
User → POST /staking/stake
     → Validate plan & amount
     → Check balance
     → Lock amount in wallet
     → Create staking position
     → Create transaction
     → Log audit

User → POST /staking/unstake/{id}
     → Check lock period
     → Calculate rewards
     → Unlock principal
     → Add rewards to balance
     → Update position status
     → Create transactions
     → Log audit
```

### 4. Admin Approval Flow
```
User → POST /wallets/deposit
     → Create deposit request
     → Set status: pending

Admin → GET /admin/deposits
      → View pending deposits

Admin → PUT /admin/deposits/{id}/process
      → If approved:
          → Add to user wallet
          → Update transaction status
      → If rejected:
          → Update transaction status
      → Log audit
```

---

## 🎨 Frontend Structure (Planned)

```
/app/frontend/
│
├── public/                      # Static files
│   ├── index.html
│   └── assets/
│
├── src/
│   ├── components/              # React components
│   │   ├── auth/
│   │   │   ├── LoginForm.jsx
│   │   │   ├── RegisterForm.jsx
│   │   │   ├── TwoFactorSetup.jsx
│   │   │   └── GoogleOAuthButton.jsx
│   │   │
│   │   ├── documents/
│   │   │   ├── DocumentList.jsx
│   │   │   ├── DocumentCard.jsx
│   │   │   ├── DocumentUpload.jsx
│   │   │   └── DocumentDetails.jsx
│   │   │
│   │   ├── wallet/
│   │   │   ├── WalletBalance.jsx
│   │   │   ├── DepositForm.jsx
│   │   │   ├── WithdrawForm.jsx
│   │   │   └── TransactionHistory.jsx
│   │   │
│   │   ├── crypto/
│   │   │   ├── CryptoWalletList.jsx
│   │   │   ├── CryptoDeposit.jsx
│   │   │   └── CryptoWithdraw.jsx
│   │   │
│   │   ├── staking/
│   │   │   ├── StakingPlans.jsx
│   │   │   ├── StakeForm.jsx
│   │   │   └── StakingPositions.jsx
│   │   │
│   │   ├── investments/
│   │   │   ├── InvestmentPackages.jsx
│   │   │   ├── InvestmentPortfolio.jsx
│   │   │   └── DocumentInvestments.jsx
│   │   │
│   │   ├── admin/
│   │   │   ├── Dashboard.jsx
│   │   │   ├── UserManagement.jsx
│   │   │   ├── DocumentApproval.jsx
│   │   │   ├── KYCVerification.jsx
│   │   │   └── Analytics.jsx
│   │   │
│   │   └── ui/                  # Shadcn components
│   │       ├── button.jsx
│   │       ├── card.jsx
│   │       ├── dialog.jsx
│   │       ├── form.jsx
│   │       └── ...
│   │
│   ├── pages/                   # Route pages
│   │   ├── Home.jsx
│   │   ├── Login.jsx
│   │   ├── Register.jsx
│   │   ├── Dashboard.jsx
│   │   ├── Documents.jsx
│   │   ├── Wallet.jsx
│   │   ├── Staking.jsx
│   │   ├── Investments.jsx
│   │   ├── Profile.jsx
│   │   └── admin/
│   │       ├── AdminDashboard.jsx
│   │       ├── Users.jsx
│   │       └── Transactions.jsx
│   │
│   ├── services/                # API services
│   │   ├── api.js              # Axios instance
│   │   ├── authService.js
│   │   ├── documentService.js
│   │   ├── walletService.js
│   │   ├── stakingService.js
│   │   ├── investmentService.js
│   │   └── adminService.js
│   │
│   ├── context/                 # React Context
│   │   ├── AuthContext.jsx
│   │   ├── WalletContext.jsx
│   │   └── ThemeContext.jsx
│   │
│   ├── hooks/                   # Custom hooks
│   │   ├── useAuth.js
│   │   ├── useWallet.js
│   │   └── useDocuments.js
│   │
│   ├── utils/                   # Utilities
│   │   ├── formatters.js
│   │   ├── validators.js
│   │   └── constants.js
│   │
│   ├── App.jsx                  # Main App component
│   ├── App.css                  # Global styles
│   └── index.js                 # Entry point
│
├── .env                         # Environment variables
├── package.json                 # Dependencies
├── tailwind.config.js           # Tailwind config
└── postcss.config.js            # PostCSS config
```

---

## 🔄 API Request/Response Flow

### Example: User Registration
```
REQUEST:
POST /api/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "username": "username",
  "password": "SecurePass123!",
  "full_name": "John Doe"
}

BACKEND PROCESSING:
1. Validate input (Pydantic)
2. Check rate limit
3. Check existing user
4. Hash password (bcrypt)
5. Create user document
6. Create wallet document
7. Generate JWT tokens
8. Log audit

RESPONSE:
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

### Example: Stake Coins
```
REQUEST:
POST /api/staking/stake
Authorization: Bearer {token}
Content-Type: application/json

{
  "plan": "premium",
  "amount": 1000.0
}

BACKEND PROCESSING:
1. Authenticate user (middleware)
2. Check rate limit
3. Validate plan
4. Check minimum amount
5. Check user balance
6. Lock amount in wallet
7. Create staking position
8. Create transaction
9. Log audit

RESPONSE:
{
  "success": true,
  "message": "Successfully staked 1000.0 coins",
  "position": {
    "id": "...",
    "plan": "premium",
    "amount": 1000.0,
    "apy": 10,
    "locked_until": "2025-04-01T00:00:00Z"
  }
}
```

---

## 🔐 Security Layer

```
Request
  ↓
1. CORS Check
  ↓
2. Rate Limiting (100 req/min)
  ↓
3. Input Validation (Pydantic)
  ↓
4. Authentication Check (JWT/Session)
  ↓
5. Authorization Check (Role)
  ↓
6. Business Logic
  ↓
7. Audit Logging
  ↓
Response
```

---

## 📈 Key Features Summary

### ✅ Implemented
- JWT + 2FA + OAuth Authentication
- User & KYC Management
- Document Upload/Download (GridFS)
- Internal Wallet System
- Cryptocurrency Wallets (BTC/ETH)
- Staking (3 plans: Basic, Premium, VIP)
- Investment Packages (3 tiers)
- Document Investment
- Admin Panel (full CRUD)
- Audit Logging
- Rate Limiting
- Security Best Practices

### 🚧 Pending
- Frontend UI Development
- Real Crypto Integration (Coinbase/Web3)
- Email Notifications
- SMS 2FA
- WebSocket Real-time Updates
- Mobile App

---

## 📝 Quick Commands

```bash
# Backend
cd /app/backend
pip install -r requirements.txt
sudo supervisorctl restart backend
tail -f /var/log/supervisor/backend.*.log

# Test API
curl http://localhost:8001/api/health
curl http://localhost:8001/api/staking/plans

# MongoDB
mongosh mongodb://localhost:27017
use document_exchange
show collections
db.users.find().pretty()

# Frontend (when ready)
cd /app/frontend
yarn install
yarn start
```

---

**Phát triển bởi:** Emergent Labs  
**Status:** ✅ Backend Complete | 🚧 Frontend Pending  
**Version:** 1.0.0
