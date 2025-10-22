# API Endpoints Summary - Document Exchange Platform

## 🎯 Tổng quan
**Tổng số: 52 API endpoints** được phân chia thành 9 modules chính

---

## 📋 Danh sách Endpoints đầy đủ

### 1️⃣ Authentication (9 endpoints)
```
POST   /api/auth/register           - Đăng ký tài khoản
POST   /api/auth/login              - Đăng nhập (hỗ trợ 2FA)
POST   /api/auth/refresh            - Refresh token
POST   /api/auth/2fa/setup          - Thiết lập 2FA
POST   /api/auth/2fa/verify         - Xác minh 2FA
POST   /api/auth/2fa/disable        - Tắt 2FA
GET    /api/auth/google/login       - Google OAuth URL
POST   /api/auth/session            - Tạo session OAuth
POST   /api/auth/logout             - Đăng xuất
```

### 2️⃣ User Management (4 endpoints)
```
GET    /api/users/profile           - Lấy profile
PUT    /api/users/profile           - Cập nhật profile
POST   /api/users/kyc               - Submit KYC
GET    /api/users/kyc/status        - Trạng thái KYC
```

### 3️⃣ Documents (6 endpoints)
```
POST   /api/documents               - Upload tài liệu
GET    /api/documents               - Danh sách tài liệu
GET    /api/documents/{id}          - Chi tiết tài liệu
POST   /api/documents/{id}/purchase - Mua tài liệu
GET    /api/documents/{id}/download - Tải tài liệu
DELETE /api/documents/{id}          - Xóa tài liệu
```

### 4️⃣ Wallets (4 endpoints)
```
GET    /api/wallets/balance         - Xem số dư
POST   /api/wallets/deposit         - Nạp tiền
POST   /api/wallets/withdraw        - Rút tiền
GET    /api/wallets/transactions    - Lịch sử giao dịch
```

### 5️⃣ Cryptocurrency (7 endpoints)
```
POST   /api/crypto/wallets/create   - Tạo ví BTC/ETH
GET    /api/crypto/wallets          - Danh sách ví crypto
GET    /api/crypto/wallets/{id}/balance - Số dư ví
POST   /api/crypto/deposit          - Nạp crypto
POST   /api/crypto/withdraw         - Rút crypto
GET    /api/crypto/transactions     - Lịch sử crypto
GET    /api/crypto/rates            - Tỷ giá hiện tại
```

### 6️⃣ Staking (5 endpoints)
```
GET    /api/staking/plans           - Gói staking
POST   /api/staking/stake           - Stake coins
POST   /api/staking/unstake/{id}    - Unstake coins
GET    /api/staking/positions       - Vị thế staking
GET    /api/staking/rewards         - Rewards đã nhận
```

### 7️⃣ Investments (4 endpoints)
```
GET    /api/investments/packages    - Gói đầu tư
POST   /api/investments/purchase    - Mua gói đầu tư
GET    /api/investments/portfolio   - Danh mục đầu tư
GET    /api/investments/returns     - Lợi nhuận
```

### 8️⃣ Document Investments (3 endpoints)
```
POST   /api/document-investments/invest    - Đầu tư vào tài liệu
GET    /api/document-investments/portfolio - Danh mục
GET    /api/document-investments/returns   - Lợi nhuận
```

### 9️⃣ Admin Panel (13 endpoints)

#### User Management
```
GET    /api/admin/users             - Danh sách users
GET    /api/admin/users/{id}        - Chi tiết user
PUT    /api/admin/users/{id}/verify-kyc - Duyệt KYC
PUT    /api/admin/users/{id}/role   - Đổi role
```

#### Document Management
```
GET    /api/admin/documents         - Danh sách tài liệu
PUT    /api/admin/documents/{id}/approve - Duyệt tài liệu
```

#### Transaction Management
```
GET    /api/admin/transactions      - Tất cả giao dịch
```

#### Deposit/Withdrawal Processing
```
GET    /api/admin/deposits          - Yêu cầu nạp tiền
PUT    /api/admin/deposits/{id}/process - Xử lý nạp
GET    /api/admin/withdrawals       - Yêu cầu rút tiền
PUT    /api/admin/withdrawals/{id}/process - Xử lý rút
```

#### Analytics & Logs
```
GET    /api/admin/analytics         - Thống kê
GET    /api/admin/audit-logs        - Audit logs
```

---

## 🗂️ Database Collections (13 collections)

```
1.  users                    - Người dùng
2.  sessions                 - Phiên đăng nhập
3.  documents                - Tài liệu
4.  wallets                  - Ví coin nội bộ
5.  crypto_wallets           - Ví BTC/ETH
6.  transactions             - Giao dịch
7.  staking_positions        - Vị thế staking
8.  investment_positions     - Gói đầu tư
9.  document_investments     - Đầu tư tài liệu
10. kyc_submissions          - Hồ sơ KYC
11. deposit_requests         - Yêu cầu nạp
12. withdrawal_requests      - Yêu cầu rút
13. audit_logs               - Nhật ký hệ thống
```

---

## 🎨 Frontend Pages Plan (20+ pages)

### Public Pages
```
/                   - Landing page
/login              - Đăng nhập
/register           - Đăng ký
```

### User Pages (Protected)
```
/dashboard          - Dashboard tổng quan
/documents          - Marketplace
/documents/:id      - Chi tiết tài liệu
/documents/upload   - Upload tài liệu
/wallet             - Quản lý ví
/crypto             - Ví cryptocurrency
/staking            - Staking dashboard
/investments        - Danh mục đầu tư
/profile            - Profile & settings
/profile/kyc        - Submit KYC
/profile/security   - Bảo mật & 2FA
```

### Admin Pages (Admin only)
```
/admin              - Admin dashboard
/admin/users        - Quản lý users
/admin/documents    - Duyệt tài liệu
/admin/kyc          - Xác minh KYC
/admin/transactions - Giao dịch
/admin/deposits     - Duyệt nạp tiền
/admin/withdrawals  - Duyệt rút tiền
/admin/analytics    - Thống kê
/admin/logs         - Audit logs
```

---

## 🔐 Security Features

✅ JWT Authentication (Access + Refresh Token)
✅ 2FA với TOTP (Google Authenticator)
✅ Google OAuth 2.0 Social Login
✅ bcrypt Password Hashing
✅ Rate Limiting (100 req/min per IP)
✅ Session Management (httpOnly cookies)
✅ Audit Logging (mọi action)
✅ Input Validation (Pydantic)
✅ CORS Protection
✅ GridFS File Storage
✅ MongoDB Injection Prevention

---

## 💰 Investment Features

### Staking Plans
- **Basic**: 100 coin min, 5% APY, 30 days
- **Premium**: 1000 coin min, 10% APY, 90 days
- **VIP**: 10000 coin min, 15% APY, 180 days

### Investment Packages
- **Starter**: $500, 8% return, 60 days
- **Growth**: $2000, 12% return, 90 days
- **Premium**: $10000, 18% return, 180 days

### Document Investment
- Đầu tư vào tài liệu để nhận revenue share
- Share percentage tính theo số tiền đầu tư
- Nhận lợi nhuận mỗi khi tài liệu được bán

---

## 📊 Technology Stack

### Backend
```
FastAPI          - Web framework
MongoDB          - Database
Motor            - Async MongoDB driver
Pydantic         - Data validation
JWT              - Authentication
PyOTP            - 2FA
bcrypt           - Password hashing
httpx            - HTTP client
GridFS           - File storage
```

### Frontend (Planned)
```
React 19         - UI framework
TailwindCSS      - Styling
Shadcn UI        - Component library
Axios            - API client
React Router     - Routing
React Hook Form  - Forms
Zod              - Validation
Sonner           - Toasts
```

---

## 🚀 Quick Start

### Test Backend API
```bash
# Health check
curl http://localhost:8001/api/health

# Staking plans
curl http://localhost:8001/api/staking/plans

# Investment packages
curl http://localhost:8001/api/investments/packages

# Crypto rates
curl http://localhost:8001/api/crypto/rates
```

### Create Admin User
```bash
mongosh mongodb://localhost:27017

use document_exchange

db.users.insertOne({
  id: "admin-001",
  email: "admin@example.com",
  username: "admin",
  password_hash: "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5QkiW0HkCzzHm",
  role: "admin",
  kyc_status: "verified",
  is_active: true,
  is_2fa_enabled: false,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString()
})
```

---

## ✅ Status

- ✅ **Backend API**: Complete (52 endpoints)
- ✅ **Database Schema**: Complete (13 collections)
- ✅ **Security Features**: Complete
- ✅ **Documentation**: Complete
- 🚧 **Frontend**: Pending development
- 🚧 **Crypto Integration**: Mocked (needs real API keys)

---

## 📝 Next Steps

1. ✅ Backend API hoàn thành
2. 🚧 Phát triển Frontend React
3. 🚧 Tích hợp Frontend với Backend
4. 🚧 Testing end-to-end
5. 🚧 Tích hợp Coinbase/Web3 API thật
6. 🚧 Deploy production

---

**Base URL:** `https://document-exchange.preview.emergentagent.com/api`  
**Documentation:** See `/app/README.md` for full details  
**Version:** 1.0.0  
**Status:** Backend Complete ✅
