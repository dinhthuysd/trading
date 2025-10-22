# Document Exchange Platform - Complete Documentation

## 📋 Tổng quan

Hệ thống backend API bảo mật cao cho nền tảng mua bán tài liệu với tích hợp tiền ảo, staking và đầu tư.

### 🔐 Tính năng bảo mật

- **Authentication & Authorization**
  - JWT Token (HS256) với Access & Refresh Token  
  - 2FA (Two-Factor Authentication) với TOTP
  - Google OAuth 2.0 Social Login (Emergent Integration)
  - Session Management với httpOnly cookies
  - Password hashing với bcrypt
  
- **Security Features**
  - Rate limiting (100 requests/minute per IP)
  - Input validation với Pydantic models
  - Audit logging cho mọi hành động quan trọng
  - CORS protection
  - Timezone-aware datetime handling
  - MongoDB injection prevention
  
- **Data Protection**
  - Encrypted password storage
  - Secure token generation
  - API key encryption
  - GridFS cho file storage an toàn

---

## 🏗️ Kiến trúc hệ thống

### Backend Stack
```
FastAPI (Python 3.11+)
├── MongoDB (Database + GridFS)
├── Motor (Async MongoDB Driver)
├── Pydantic (Data Validation)
├── JWT (Authentication)
├── PyOTP (2FA)
└── bcrypt (Password Hashing)
```

### Project Structure
```
/app/
├── backend/
│   ├── server.py                    # Main FastAPI application
│   ├── config.py                    # Configuration & settings
│   ├── database.py                  # MongoDB connection & indexes
│   ├── models.py                    # Pydantic models
│   ├── security.py                  # Security utilities (JWT, hashing)
│   ├── middleware.py                # Auth & rate limiting middleware
│   ├── .env                         # Environment variables
│   ├── requirements.txt             # Python dependencies
│   └── routes/
│       ├── __init__.py
│       ├── auth.py                  # Authentication endpoints
│       ├── users.py                 # User management
│       ├── documents.py             # Document CRUD & purchases
│       ├── wallets.py               # Internal coin wallet
│       ├── crypto.py                # Cryptocurrency (BTC/ETH)
│       ├── staking.py               # Staking functionality
│       ├── investments.py           # Investment packages
│       ├── document_investments.py  # Document investment
│       └── admin.py                 # Admin panel APIs
│
└── frontend/                        # (Sẽ phát triển sau)
    └── ...
```

---

## 📊 Database Schema - Danh sách Collections

### 1. **users** - Quản lý người dùng
- Lưu trữ thông tin user, authentication, KYC status
- Fields: id, email, username, password_hash, role, kyc_status, 2FA settings

### 2. **sessions** - Quản lý phiên đăng nhập
- Session tokens từ OAuth và JWT
- Fields: session_token, user_id, expires_at

### 3. **documents** - Tài liệu bán
- Metadata và link GridFS của file
- Fields: title, description, price, seller_id, file_id, status, revenue

### 4. **wallets** - Ví coin nội bộ
- Balance và locked balance cho staking/investment
- Fields: user_id, balance, locked_balance

### 5. **crypto_wallets** - Ví tiền ảo (BTC/ETH)
- Địa chỉ và số dư crypto
- Fields: user_id, crypto_type, address, balance

### 6. **transactions** - Lịch sử giao dịch
- Tất cả các loại transaction
- Fields: user_id, type, amount, status, metadata

### 7. **staking_positions** - Vị thế staking
- Thông tin staking và rewards
- Fields: user_id, plan, amount, apy, locked_until, rewards_earned

### 8. **investment_positions** - Gói đầu tư
- Investment packages đã mua
- Fields: user_id, package, amount, expected_return, expires_at

### 9. **document_investments** - Đầu tư vào tài liệu
- Đầu tư để nhận revenue share
- Fields: user_id, document_id, amount, share_percentage, revenue_earned

### 10. **kyc_submissions** - Hồ sơ KYC
- Documents xác minh danh tính (GridFS)
- Fields: user_id, id_type, file_ids, status

### 11. **deposit_requests** - Yêu cầu nạp tiền
- Pending deposits chờ admin duyệt
- Fields: user_id, amount, payment_method, status

### 12. **withdrawal_requests** - Yêu cầu rút tiền
- Pending withdrawals chờ admin duyệt
- Fields: user_id, amount, withdrawal_method, status

### 13. **audit_logs** - Nhật ký hệ thống
- Log mọi hành động quan trọng
- Fields: user_id, action, details, ip_address, timestamp

---

## 🔌 Danh sách đầy đủ API Endpoints

### Base URL
```
Production: https://document-exchange.preview.emergentagent.com/api
Development: http://localhost:8001/api
```

---

## 📋 API Endpoints chi tiết

### 🔐 **AUTHENTICATION MODULE** (`/api/auth`) - 9 endpoints

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| POST | `/auth/register` | Đăng ký tài khoản mới |
| POST | `/auth/login` | Đăng nhập (hỗ trợ 2FA) |
| POST | `/auth/refresh` | Refresh access token |
| POST | `/auth/2fa/setup` | Thiết lập 2FA (QR code) |
| POST | `/auth/2fa/verify` | Xác minh và bật 2FA |
| POST | `/auth/2fa/disable` | Tắt 2FA |
| GET | `/auth/google/login` | Lấy URL Google OAuth |
| POST | `/auth/session` | Tạo session từ Google OAuth |
| POST | `/auth/logout` | Đăng xuất |

---

### 👤 **USER MODULE** (`/api/users`) - 4 endpoints

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/users/profile` | Lấy thông tin profile |
| PUT | `/users/profile` | Cập nhật profile |
| POST | `/users/kyc` | Submit KYC documents |
| GET | `/users/kyc/status` | Kiểm tra trạng thái KYC |

---

### 📄 **DOCUMENT MODULE** (`/api/documents`) - 6 endpoints

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| POST | `/documents` | Upload tài liệu để bán |
| GET | `/documents` | Danh sách tài liệu (filter, search) |
| GET | `/documents/{id}` | Chi tiết tài liệu |
| POST | `/documents/{id}/purchase` | Mua tài liệu |
| GET | `/documents/{id}/download` | Tải tài liệu đã mua |
| DELETE | `/documents/{id}` | Xóa tài liệu |

---

### 💰 **WALLET MODULE** (`/api/wallets`) - 4 endpoints

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/wallets/balance` | Xem số dư ví |
| POST | `/wallets/deposit` | Yêu cầu nạp tiền |
| POST | `/wallets/withdraw` | Yêu cầu rút tiền |
| GET | `/wallets/transactions` | Lịch sử giao dịch |

---

### ₿ **CRYPTO MODULE** (`/api/crypto`) - 7 endpoints

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| POST | `/crypto/wallets/create` | Tạo ví BTC/ETH |
| GET | `/crypto/wallets` | Danh sách ví crypto |
| GET | `/crypto/wallets/{id}/balance` | Số dư ví crypto |
| POST | `/crypto/deposit` | Nạp cryptocurrency |
| POST | `/crypto/withdraw` | Rút cryptocurrency |
| GET | `/crypto/transactions` | Lịch sử giao dịch crypto |
| GET | `/crypto/rates` | Tỷ giá BTC/ETH hiện tại |

---

### 🔒 **STAKING MODULE** (`/api/staking`) - 5 endpoints

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/staking/plans` | Danh sách gói staking |
| POST | `/staking/stake` | Stake coins |
| POST | `/staking/unstake/{id}` | Unstake và nhận rewards |
| GET | `/staking/positions` | Vị thế staking của user |
| GET | `/staking/rewards` | Tổng rewards đã nhận |

**Staking Plans:**
- Basic: 100 coin min, 5% APY, 30 days
- Premium: 1000 coin min, 10% APY, 90 days  
- VIP: 10000 coin min, 15% APY, 180 days

---

### 📈 **INVESTMENT MODULE** (`/api/investments`) - 4 endpoints

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/investments/packages` | Danh sách gói đầu tư |
| POST | `/investments/purchase` | Mua gói đầu tư |
| GET | `/investments/portfolio` | Danh mục đầu tư |
| GET | `/investments/returns` | Lợi nhuận đầu tư |

**Investment Packages:**
- Starter: $500, 8% return, 60 days
- Growth: $2000, 12% return, 90 days
- Premium: $10000, 18% return, 180 days

---

### 📊 **DOCUMENT INVESTMENT MODULE** (`/api/document-investments`) - 3 endpoints

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| POST | `/document-investments/invest` | Đầu tư vào tài liệu |
| GET | `/document-investments/portfolio` | Danh mục đầu tư tài liệu |
| GET | `/document-investments/returns` | Lợi nhuận từ tài liệu |

---

### 👨‍💼 **ADMIN MODULE** (`/api/admin`) - 13 endpoints

**Yêu cầu:** Admin role

#### User Management (4 endpoints)
| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/admin/users` | Danh sách users (filter) |
| GET | `/admin/users/{id}` | Chi tiết user |
| PUT | `/admin/users/{id}/verify-kyc` | Duyệt/từ chối KYC |
| PUT | `/admin/users/{id}/role` | Thay đổi role user |

#### Document Management (2 endpoints)
| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/admin/documents` | Danh sách tài liệu |
| PUT | `/admin/documents/{id}/approve` | Duyệt/từ chối tài liệu |

#### Transaction Management (2 endpoints)
| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/admin/transactions` | Tất cả giao dịch |
| GET | `/admin/audit-logs` | Audit logs |

#### Deposit/Withdrawal Processing (4 endpoints)
| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/admin/deposits` | Yêu cầu nạp tiền |
| PUT | `/admin/deposits/{id}/process` | Xử lý nạp tiền |
| GET | `/admin/withdrawals` | Yêu cầu rút tiền |
| PUT | `/admin/withdrawals/{id}/process` | Xử lý rút tiền |

#### Analytics (1 endpoint)
| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/admin/analytics` | Thống kê tổng quan |

---

## 📊 Tổng kết API Endpoints

### Tổng số endpoints: **52 endpoints**

**Phân loại theo module:**
- Authentication: 9 endpoints
- Users: 4 endpoints
- Documents: 6 endpoints
- Wallets: 4 endpoints
- Cryptocurrency: 7 endpoints
- Staking: 5 endpoints
- Investments: 4 endpoints
- Document Investments: 3 endpoints
- Admin: 13 endpoints

**Phân loại theo HTTP method:**
- GET: 23 endpoints (Read operations)
- POST: 19 endpoints (Create operations)
- PUT: 9 endpoints (Update operations)
- DELETE: 1 endpoint (Delete operations)

---

## 🎨 Frontend Development Plan

### Cấu trúc Frontend (React + TailwindCSS + Shadcn UI)

```
/app/frontend/
├── src/
│   ├── components/
│   │   ├── auth/
│   │   │   ├── LoginForm.jsx
│   │   │   ├── RegisterForm.jsx
│   │   │   ├── TwoFactorSetup.jsx
│   │   │   └── GoogleOAuthButton.jsx
│   │   ├── documents/
│   │   │   ├── DocumentList.jsx
│   │   │   ├── DocumentCard.jsx
│   │   │   ├── DocumentUpload.jsx
│   │   │   ├── DocumentDetails.jsx
│   │   │   └── DocumentPurchase.jsx
│   │   ├── wallet/
│   │   │   ├── WalletBalance.jsx
│   │   │   ├── DepositForm.jsx
│   │   │   ├── WithdrawForm.jsx
│   │   │   └── TransactionHistory.jsx
│   │   ├── crypto/
│   │   │   ├── CryptoWalletList.jsx
│   │   │   ├── CreateCryptoWallet.jsx
│   │   │   ├── CryptoDeposit.jsx
│   │   │   ├── CryptoWithdraw.jsx
│   │   │   └── CryptoRates.jsx
│   │   ├── staking/
│   │   │   ├── StakingPlans.jsx
│   │   │   ├── StakePlanCard.jsx
│   │   │   ├── StakeForm.jsx
│   │   │   ├── StakingPositions.jsx
│   │   │   └── UnstakeButton.jsx
│   │   ├── investments/
│   │   │   ├── InvestmentPackages.jsx
│   │   │   ├── PackageCard.jsx
│   │   │   ├── InvestmentPortfolio.jsx
│   │   │   ├── DocumentInvestments.jsx
│   │   │   └── InvestmentReturns.jsx
│   │   ├── admin/
│   │   │   ├── Dashboard.jsx
│   │   │   ├── UserManagement.jsx
│   │   │   ├── UserDetailsModal.jsx
│   │   │   ├── DocumentApproval.jsx
│   │   │   ├── KYCVerification.jsx
│   │   │   ├── DepositApproval.jsx
│   │   │   ├── WithdrawalApproval.jsx
│   │   │   ├── Analytics.jsx
│   │   │   ├── AnalyticsCard.jsx
│   │   │   └── AuditLogs.jsx
│   │   ├── profile/
│   │   │   ├── ProfileForm.jsx
│   │   │   ├── KYCSubmission.jsx
│   │   │   ├── KYCStatus.jsx
│   │   │   └── SecuritySettings.jsx
│   │   ├── layout/
│   │   │   ├── Navbar.jsx
│   │   │   ├── Sidebar.jsx
│   │   │   ├── Footer.jsx
│   │   │   └── PageHeader.jsx
│   │   └── ui/ (Shadcn components)
│   │       ├── button.jsx
│   │       ├── card.jsx
│   │       ├── dialog.jsx
│   │       ├── form.jsx
│   │       ├── input.jsx
│   │       ├── table.jsx
│   │       ├── tabs.jsx
│   │       ├── toast.jsx
│   │       └── ...
│   ├── pages/
│   │   ├── Home.jsx
│   │   ├── Login.jsx
│   │   ├── Register.jsx
│   │   ├── Dashboard.jsx
│   │   ├── Documents.jsx
│   │   ├── DocumentDetails.jsx
│   │   ├── Wallet.jsx
│   │   ├── Crypto.jsx
│   │   ├── Staking.jsx
│   │   ├── Investments.jsx
│   │   ├── Profile.jsx
│   │   └── admin/
│   │       ├── AdminDashboard.jsx
│   │       ├── Users.jsx
│   │       ├── Documents.jsx
│   │       ├── Transactions.jsx
│   │       ├── Deposits.jsx
│   │       ├── Withdrawals.jsx
│   │       └── Analytics.jsx
│   ├── services/
│   │   ├── api.js (Axios configuration)
│   │   ├── authService.js
│   │   ├── userService.js
│   │   ├── documentService.js
│   │   ├── walletService.js
│   │   ├── cryptoService.js
│   │   ├── stakingService.js
│   │   ├── investmentService.js
│   │   └── adminService.js
│   ├── context/
│   │   ├── AuthContext.jsx
│   │   ├── WalletContext.jsx
│   │   └── ThemeContext.jsx
│   ├── hooks/
│   │   ├── useAuth.js
│   │   ├── useWallet.js
│   │   ├── useDocuments.js
│   │   └── useToast.js
│   ├── utils/
│   │   ├── formatters.js
│   │   ├── validators.js
│   │   └── constants.js
│   ├── App.jsx
│   ├── App.css
│   └── index.js
└── package.json
```

---

### Frontend Routes (React Router)

```javascript
// Public Routes
/ - Landing page (Hero, features, pricing)
/login - Login page
/register - Registration page

// Protected Routes (User)
/dashboard - User dashboard overview
/documents - Document marketplace (browse, search)
/documents/:id - Document details
/documents/upload - Upload document for sale
/wallet - Wallet management (balance, deposit, withdraw)
/crypto - Cryptocurrency wallets
/staking - Staking dashboard
/investments - Investment portfolio
/profile - User profile & settings
/profile/kyc - KYC submission
/profile/security - 2FA settings

// Admin Routes (Admin only)
/admin - Admin dashboard
/admin/users - User management
/admin/documents - Document approval
/admin/kyc - KYC verification
/admin/transactions - Transaction management
/admin/deposits - Deposit approval
/admin/withdrawals - Withdrawal approval
/admin/analytics - Platform analytics
/admin/logs - Audit logs
```

---

### Frontend Pages chi tiết

#### 1. **Landing Page** (`/`)
- Hero section
- Features showcase
- Staking & Investment plans
- How it works
- CTA buttons

#### 2. **User Dashboard** (`/dashboard`)
- Wallet balance overview
- Recent transactions
- Active staking positions
- Investment portfolio summary
- Quick actions

#### 3. **Document Marketplace** (`/documents`)
- Document grid/list view
- Search & filters (category, price, tags)
- Sort options
- Pagination
- Document cards with preview

#### 4. **Wallet Page** (`/wallet`)
- Balance display (available, locked)
- Deposit form
- Withdraw form
- Transaction history table
- Crypto wallet section

#### 5. **Staking Page** (`/staking`)
- Staking plans cards
- Current positions
- Rewards calculator
- Unstake functionality
- APY comparison

#### 6. **Investments Page** (`/investments`)
- Investment packages
- Portfolio overview
- Document investments
- Returns tracking
- Performance charts

#### 7. **Admin Dashboard** (`/admin`)
- Overview statistics
- Pending requests count
- Recent activity
- Quick actions
- Analytics charts

#### 8. **Admin - User Management** (`/admin/users`)
- User list table
- Search & filters
- KYC status indicators
- Role management
- User details modal

#### 9. **Admin - Document Approval** (`/admin/documents`)
- Pending documents queue
- Document preview
- Approve/Reject actions
- Rejection reason form

#### 10. **Admin - Deposit/Withdrawal** (`/admin/deposits`, `/admin/withdrawals`)
- Pending requests table
- Payment proof display
- Approve/Reject actions
- Transaction hash input (withdrawals)

---

## 🚀 Installation & Deployment

### Backend Setup

```bash
# Navigate to backend
cd /app/backend

# Install dependencies (already done)
pip install -r requirements.txt

# Environment variables
# Edit .env file with your configurations

# Restart backend
sudo supervisorctl restart backend

# Check status
sudo supervisorctl status backend

# View logs
tail -f /var/log/supervisor/backend.*.log
```

### Frontend Setup (Khi phát triển)

```bash
# Navigate to frontend
cd /app/frontend

# Install dependencies
yarn install

# Start development server
yarn start

# Build for production
yarn build
```

---

## 🔧 Configuration

### Environment Variables

```bash
# Backend (.env)
MONGO_URL="mongodb://localhost:27017"
DB_NAME="document_exchange"
JWT_SECRET_KEY="your-secret-key-min-32-chars"
CORS_ORIGINS="*"

# Cryptocurrency (Replace with real API keys)
COINBASE_API_KEY="your-coinbase-api-key"
COINBASE_API_SECRET="your-coinbase-api-secret"
WEB3_INFURA_URL="https://mainnet.infura.io/v3/your-key"

# Frontend (.env)
REACT_APP_BACKEND_URL=https://document-exchange.preview.emergentagent.com
```

### Staking Plans Configuration

```python
# config.py
STAKING_PLANS = {
    'basic': {'min_amount': 100, 'apy': 5, 'lock_days': 30},
    'premium': {'min_amount': 1000, 'apy': 10, 'lock_days': 90},
    'vip': {'min_amount': 10000, 'apy': 15, 'lock_days': 180}
}
```

### Investment Packages Configuration

```python
# config.py
INVESTMENT_PACKAGES = {
    'starter': {'price': 500, 'expected_return': 8, 'duration_days': 60},
    'growth': {'price': 2000, 'expected_return': 12, 'duration_days': 90},
    'premium': {'price': 10000, 'expected_return': 18, 'duration_days': 180}
}
```

---

## 🧪 Testing

### Create Admin User

```javascript
// MongoDB command
use document_exchange

db.users.insertOne({
  id: "admin-001",
  email: "admin@example.com",
  username: "admin",
  password_hash: "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5QkiW0HkCzzHm", // Hash of "Admin@123"
  role: "admin",
  is_active: true,
  is_2fa_enabled: false,
  kyc_status: "verified",
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString()
})

// Create wallet for admin
db.wallets.insertOne({
  user_id: "admin-001",
  balance: 100000.0,
  locked_balance: 0.0,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString()
})
```

### API Testing Examples

```bash
# Health check
curl http://localhost:8001/api/health

# Register
curl -X POST http://localhost:8001/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","username":"testuser","password":"Test123!","full_name":"Test User"}'

# Login
curl -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test123!"}'

# Get balance (replace {token})
curl http://localhost:8001/api/wallets/balance \
  -H "Authorization: Bearer {token}"

# Get staking plans
curl http://localhost:8001/api/staking/plans

# Get crypto rates
curl http://localhost:8001/api/crypto/rates
```

---

## 📝 Important Notes

### Security Best Practices

1. **Production Checklist:**
   - [ ] Change JWT_SECRET_KEY to strong random string
   - [ ] Use HTTPS only
   - [ ] Restrict CORS_ORIGINS to specific domains
   - [ ] Use strong passwords for admin accounts
   - [ ] Enable 2FA for all admin accounts
   - [ ] Regular security audits
   - [ ] Monitor audit logs

2. **Cryptocurrency Integration:**
   - Current implementation is **MOCKED**
   - Replace with real Coinbase/Web3 integration
   - Test with testnet before mainnet
   - Implement proper key management
   - Add transaction confirmation logic

3. **File Upload:**
   - Maximum file size: 100MB
   - Allowed types: pdf, doc, docx, txt, xls, xlsx, ppt, pptx, zip, rar
   - Files stored in MongoDB GridFS
   - Consider cloud storage (S3) for scalability

4. **Rate Limiting:**
   - Adjust based on server capacity
   - Consider Redis for distributed rate limiting
   - Monitor and adjust thresholds

---

## 🔄 Development Workflow

### Phase 1: ✅ Backend API (COMPLETED)
- [x] Database schema design
- [x] Authentication system (JWT + 2FA + OAuth)
- [x] User management
- [x] Document CRUD with GridFS
- [x] Wallet system
- [x] Crypto integration (mocked)
- [x] Staking functionality
- [x] Investment packages
- [x] Document investments
- [x] Admin panel APIs
- [x] Security features (rate limiting, audit logs)
- [x] Complete API documentation

### Phase 2: Frontend Development (TODO)
- [ ] Setup React project structure
- [ ] Implement authentication UI
- [ ] User dashboard
- [ ] Document marketplace
- [ ] Wallet management UI
- [ ] Staking interface
- [ ] Investment portfolio
- [ ] Admin panel UI
- [ ] Responsive design
- [ ] Testing & optimization

### Phase 3: Integration & Testing (TODO)
- [ ] Connect frontend to backend API
- [ ] E2E testing
- [ ] Security testing
- [ ] Performance optimization
- [ ] Bug fixes

### Phase 4: Production Deployment (TODO)
- [ ] Setup production environment
- [ ] SSL certificates
- [ ] Database backup strategy
- [ ] Monitoring & logging
- [ ] CI/CD pipeline

---

## 📈 Future Enhancements

1. **Email Notifications**
   - Welcome emails
   - Transaction notifications
   - KYC status updates
   - Withdrawal confirmations

2. **Advanced Features**
   - Referral program
   - Affiliate system
   - Multi-language support
   - Mobile app (React Native)
   - WebSocket for real-time updates

3. **Analytics**
   - Advanced charts & graphs
   - User behavior tracking
   - Revenue forecasting
   - Performance metrics

4. **Payment Integration**
   - Stripe integration
   - PayPal integration
   - More crypto support (USDT, BNB, etc.)

5. **Social Features**
   - User ratings & reviews
   - Document comments
   - Follow sellers
   - Wishlist

---

## 🆘 Troubleshooting

### Backend not starting?
```bash
# Check logs
tail -f /var/log/supervisor/backend.*.log

# Check supervisor status
sudo supervisorctl status

# Restart backend
sudo supervisorctl restart backend

# Check MongoDB connection
mongosh mongodb://localhost:27017
```

### Database errors?
```bash
# Connect to MongoDB
mongosh mongodb://localhost:27017

# Switch to database
use document_exchange

# List collections
show collections

# Check indexes
db.users.getIndexes()
```

### Import errors?
```bash
# Reinstall dependencies
cd /app/backend
pip install -r requirements.txt
```

---

## 📞 Support

Để được hỗ trợ:
1. Check documentation
2. Review logs
3. Check database connections
4. Review environment variables

---

## 📄 License

Proprietary - All rights reserved

---

**Version:** 1.0.0  
**Last Updated:** October 21, 2025  
**Developed by:** Emergent Labs  
**Status:** ✅ Backend API Complete | 🚧 Frontend Development Pending
