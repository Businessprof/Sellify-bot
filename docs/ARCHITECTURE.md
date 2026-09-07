# Architecture & Specification: Qamify-Style Telegram Digital Products Store Bot

## 1. Executive Summary & System Overview

This document specifies the end-to-end architecture, database schema, service layer, security model, and implementation roadmap for a production-grade Telegram digital products and services e-commerce bot modeled after the high-conversion Qamify flow.

The system is designed to provide:
- **Telegram Bot Client** powered by `aiogram 3.x`, featuring interactive inline keyboards, mandatory channel/group membership gating, dynamic UI rendering, and sub-second response times.
- **FastAPI Backend** providing a high-performance REST API, reseller endpoints, payment webhook processors, and server-rendered Web Admin Dashboard.
- **PostgreSQL Database** running under SQLAlchemy 2.0 Async, strictly enforcing financial atomicity, row-level concurrency locks (`SELECT ... FOR UPDATE`), and relational integrity.
- **Redis Layer** for distributed caching, aiogram FSM storage, rate limiting, and temporary lock management.
- **Background Notification & Worker System** for broadcast campaigns, order auto-delivery, support routing, and public channel live sales notifications.

```
                         TELEGRAM CLIENTS
                                │
               ┌────────────────┴────────────────┐
               │                                 │
        Telegram Bot API                  Telegram Mini App
               │                                 │
               ▼                                 ▼
      ┌─────────────────┐               ┌─────────────────┐
      │  NGINX Reverse  │───────────────│ Static Mini App │
      │  Proxy & SSL    │               │ (Frontend UI)   │
      └────────┬────────┘               └─────────────────┘
               │
        Webhook / HTTP
               │
               ▼
   ┌─────────────────────────────────────────────────────────┐
   │                    FASTAPI BACKEND                      │
   │                                                         │
   │  ┌─────────────────────┐       ┌─────────────────────┐  │
   │  │   aiogram 3 Bot     │       │    FastAPI Routers  │  │
   │  │   - Handlers        │       │    - Reseller API   │  │
   │  │   - Keyboards       │       │    - Webhooks       │  │
   │  │   - Middlewares     │       │    - Admin Web API  │  │
   │  └──────────┬──────────┘       └──────────┬──────────┘  │
   │             │                             │             │
   │             ▼                             ▼             │
   │  ┌───────────────────────────────────────────────────┐  │
   │  │                   SERVICE LAYER                   │  │
   │  │  - OrderService          - WalletService          │  │
   │  │  - InventoryService      - ReferralService        │  │
   │  │  - MembershipService     - SupportService         │  │
   │  │  - FreebieService        - NotificationService    │  │
   │  └──────────────────────────┬────────────────────────┘  │
   └─────────────────────────────┼───────────────────────────┘
                                 │
               ┌─────────────────┴─────────────────┐
               ▼                                   ▼
      ┌─────────────────┐                 ┌─────────────────┐
      │ PostgreSQL DB   │                 │      Redis      │
      │ (ACID & Locks)  │                 │ (Cache & FSM)   │
      └─────────────────┘                 └─────────────────┘
```

---

## 2. Directory Structure

```
qamify-bot/
├── app/
│   ├── __init__.py
│   ├── main.py                          # Application entrypoint (FastAPI + Bot runner)
│   ├── api/                             # FastAPI endpoints
│   │   ├── __init__.py
│   │   ├── deps.py                      # Dependency injection (DB session, auth, rate limit)
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── router.py                # Main API v1 aggregator
│   │   │   └── endpoints/
│   │   │       ├── admin.py             # Admin web panel API
│   │   │       ├── auth.py              # Admin login & JWT
│   │   │       ├── miniapp.py           # Telegram Mini App endpoints
│   │   │       ├── reseller.py          # Reseller API endpoints
│   │   │       └── webhooks.py          # Telegram & Payment webhooks
│   ├── bot/                             # aiogram 3.x Telegram Bot
│   │   ├── __init__.py
│   │   ├── bot_instance.py              # Bot & Dispatcher singleton setup
│   │   ├── filters/                     # Custom aiogram filters (AdminFilter, RoleFilter)
│   │   │   ├── __init__.py
│   │   │   └── admin_filter.py
│   │   ├── handlers/                    # Message & Callback Query handlers
│   │   │   ├── __init__.py
│   │   │   ├── start.py                 # /start, deep links, membership gate
│   │   │   ├── menu.py                  # Main menu navigation
│   │   │   ├── shop.py                  # Browse categories, products, variants, buy
│   │   │   ├── wallet.py                # Balance, top-up, transaction history
│   │   │   ├── profile.py               # User profile, statistics, settings
│   │   │   ├── referrals.py             # Deep link referral stats, referral store
│   │   │   ├── freebies.py              # Daily claims, loyalty bonuses
│   │   │   ├── support.py               # Ticket creation and reply loop
│   │   │   ├── trials.py                # Emails & trials module
│   │   │   ├── reseller.py              # Reseller API key view and regeneration
│   │   │   └── clear_chat.py            # Clean previous messages
│   │   ├── keyboards/                   # Reusable inline keyboard builders
│   │   │   ├── __init__.py
│   │   │   ├── common.py
│   │   │   ├── menu.py
│   │   │   ├── shop.py
│   │   │   ├── wallet.py
│   │   │   ├── profile.py
│   │   │   ├── referrals.py
│   │   │   └── support.py
│   │   ├── middlewares/                 # aiogram middlewares
│   │   │   ├── __init__.py
│   │   │   ├── db_session.py            # Async DB session per update
│   │   │   ├── user_tracker.py          # Auto user upsert & ban check
│   │   │   ├── membership_gate.py       # Mandatory channel/group verification
│   │   │   └── rate_limit.py            # Anti-spam throttling
│   │   └── states/                      # FSM States
│   │       ├── __init__.py
│   │       ├── shop_states.py
│   │       ├── support_states.py
│   │       └── admin_states.py
│   ├── core/                            # System-wide configuration and utilities
│   │   ├── __init__.py
│   │   ├── config.py                    # Pydantic Settings (.env loader)
│   │   ├── constants.py                 # Enums: OrderStatus, PaymentStatus, UserRole
│   │   ├── exceptions.py                # Domain exceptions
│   │   ├── logger.py                    # Structured logging setup
│   │   └── security.py                  # Hashing, API key generation, AES cipher
│   ├── database/                        # Database Layer
│   │   ├── __init__.py
│   │   ├── session.py                   # Async engine and sessionmaker
│   │   ├── base.py                      # DeclarativeBase with common mixins
│   │   ├── models/                      # SQLAlchemy 2.0 ORM Models
│   │   │   ├── __init__.py
│   │   │   ├── user.py                  # User, Admin, MembershipChannel
│   │   │   ├── wallet.py                # Wallet, WalletTransaction
│   │   │   ├── product.py               # Category, Product, ProductVariant
│   │   │   ├── inventory.py             # InventoryItem (Stock)
│   │   │   ├── order.py                 # Order, OrderItem
│   │   │   ├── referral.py              # Referral, ReferralTransaction, Reward
│   │   │   ├── freebie.py               # Freebie, FreebieClaim
│   │   │   ├── coupon.py                # Coupon, CouponRedemption
│   │   │   ├── support.py               # SupportTicket, TicketMessage
│   │   │   ├── notification.py          # Notification, Broadcast
│   │   │   ├── reseller.py              # ApiKey, ApiUsage
│   │   │   └── audit.py                 # AuditLog, Setting
│   │   └── repositories/                # Repository Pattern for data access
│   │       ├── __init__.py
│   │       ├── base.py
│   │       ├── user_repo.py
│   │       ├── wallet_repo.py
│   │       ├── product_repo.py
│   │       ├── inventory_repo.py
│   │       ├── order_repo.py
│   │       └── support_repo.py
│   ├── services/                        # Business Logic Layer
│   │   ├── __init__.py
│   │   ├── membership_service.py        # Channel/Group verification via Bot API
│   │   ├── wallet_service.py            # Atomic credit, debit, transfer, audit
│   │   ├── inventory_service.py         # Row-locked stock allocation
│   │   ├── order_service.py             # Purchase pipeline & digital delivery
│   │   ├── referral_service.py          # Deep linking, anti-abuse, commission
│   │   ├── freebie_service.py           # Claims, cooldowns, limits
│   │   ├── coupon_service.py            # Discount calculations and validation
│   │   ├── support_service.py           # Ticket lifecycle and routing
│   │   ├── notification_service.py      # User DM notifications & channel broadcasts
│   │   ├── reseller_service.py          # API authentication & instant order fulfillment
│   │   └── admin_service.py             # Management ops with mandatory audit logs
│   └── web/                             # Admin Web Panel
│       ├── templates/                   # Jinja2 HTML templates
│       │   ├── base.html
│       │   ├── dashboard.html
│       │   ├── products.html
│       │   ├── inventory.html
│       │   ├── orders.html
│       │   ├── users.html
│       │   └── settings.html
│       └── static/                      # CSS & JS assets
│           ├── css/
│           └── js/
├── docs/                                # Technical documentation & specs
│   └── ARCHITECTURE.md
├── docker/                              # Container definitions
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── nginx/default.conf
├── migrations/                          # Alembic migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── tests/                               # Comprehensive Automated Test Suite
│   ├── __init__.py
│   ├── conftest.py                      # Test fixtures, in-memory async db, bot mock
│   ├── test_bot/                        # Handlers & filters tests
│   │   ├── test_start.py
│   │   ├── test_membership.py
│   │   └── test_shop.py
│   ├── test_database/                   # Database models, constraints, migrations
│   │   ├── test_models.py
│   │   └── test_repositories.py
│   ├── test_services/                   # Service business logic & concurrency tests
│   │   ├── test_wallet_service.py
│   │   ├── test_inventory_concurrency.py
│   │   ├── test_order_service.py
│   │   └── test_referral_antiabuse.py
│   └── test_api/                        # FastAPI endpoint tests
│       └── test_reseller_api.py
├── .env.example
├── alembic.ini
├── requirements.txt
└── README.md
```

---

## 3. Database Schema Specification

### 3.1 Relational Architecture

The database uses PostgreSQL with UUID primary keys where idempotency and external exposure are critical (Orders, Transactions, Inventory), and 64-bit BigInteger for Telegram User IDs.

```
┌──────────────────┐       1:1       ┌──────────────────┐
│      users       │─────────────────│     wallets      │
└────────┬─────────┘                 └────────┬─────────┘
         │                                    │
         │ 1:N                                │ 1:N
         ▼                                    ▼
┌──────────────────┐                 ┌──────────────────┐
│      orders      │                 │wallet_transaction│
└────────┬─────────┘                 └──────────────────┘
         │
         │ 1:N
         ▼
┌──────────────────┐       N:1       ┌──────────────────┐
│   order_items    │─────────────────│ inventory_items  │
└──────────────────┘                 └────────┬─────────┘
                                              │ N:1
                                              ▼
                                     ┌──────────────────┐
                                     │ product_variants │
                                     └────────┬─────────┘
                                              │ N:1
                                              ▼
                                     ┌──────────────────┐
                                     │     products     │
                                     └────────┬─────────┘
                                              │ N:1
                                              ▼
                                     ┌──────────────────┐
                                     │product_categories│
                                     └──────────────────┘
```

### 3.2 Key Table Schemas & Constraints

#### Table: `users`
- `id`: `BigInteger`, Primary Key (Telegram User ID).
- `username`: `String(64)`, Nullable, Index.
- `first_name`: `String(255)`, Not Null.
- `last_name`: `String(255)`, Nullable.
- `membership_tier`: `Enum('BRONZE', 'SILVER', 'GOLD', 'DIAMOND')`, Default `'BRONZE'`.
- `role`: `Enum('USER', 'SUPPORT', 'FINANCE', 'INVENTORY', 'ADMIN', 'SUPER_ADMIN')`, Default `'USER'`.
- `is_banned`: `Boolean`, Default `False`, Index.
- `ban_reason`: `Text`, Nullable.
- `referral_code`: `String(32)`, Unique, Index.
- `referred_by_id`: `BigInteger`, ForeignKey(`users.id`), Nullable, Index.
- `language_code`: `String(10)`, Default `'en'`.
- `created_at`: `DateTime(timezone=True)`, ServerDefault `now()`.
- `updated_at`: `DateTime(timezone=True)`, ServerDefault `now()`, OnUpdate `now()`.
- *Constraints*: `CHECK (id != referred_by_id)` (Cannot refer self).

#### Table: `wallets`
- `id`: `UUID`, Primary Key, Default `gen_random_uuid()`.
- `user_id`: `BigInteger`, ForeignKey(`users.id`, ondelete='CASCADE'), Unique, Index.
- `balance`: `Numeric(12, 2)`, Default `0.00`, Not Null.
- `total_deposited`: `Numeric(12, 2)`, Default `0.00`, Not Null.
- `total_spent`: `Numeric(12, 2)`, Default `0.00`, Not Null.
- `currency`: `String(3)`, Default `'USD'`.
- `version`: `Integer`, Default `1`, Not Null (Optimistic Concurrency Counter).
- `updated_at`: `DateTime(timezone=True)`, ServerDefault `now()`.
- *Constraints*: `CHECK (balance >= 0.00)`.

#### Table: `wallet_transactions`
- `id`: `UUID`, Primary Key, Default `gen_random_uuid()`.
- `wallet_id`: `UUID`, ForeignKey(`wallets.id`), Index.
- `user_id`: `BigInteger`, ForeignKey(`users.id`), Index.
- `type`: `Enum('DEPOSIT', 'ORDER_PAYMENT', 'ORDER_REFUND', 'REFERRAL_BONUS', 'FREEBIE_BONUS', 'ADMIN_ADJUSTMENT')`, Index.
- `amount`: `Numeric(12, 2)`, Not Null (Positive for credits, negative for debits).
- `balance_before`: `Numeric(12, 2)`, Not Null.
- `balance_after`: `Numeric(12, 2)`, Not Null.
- `reference_id`: `String(128)`, Nullable, Index (e.g. Order ID, Payment Gateway Invoice ID).
- `idempotency_key`: `String(128)`, Unique, Nullable, Index.
- `description`: `Text`, Not Null.
- `created_at`: `DateTime(timezone=True)`, ServerDefault `now()`.

#### Table: `product_categories`
- `id`: `Integer`, Primary Key, Autoincrement.
- `name`: `String(100)`, Not Null.
- `slug`: `String(100)`, Unique, Index.
- `icon`: `String(32)`, Default `'📦'`.
- `display_order`: `Integer`, Default `0`.
- `is_active`: `Boolean`, Default `True`, Index.

#### Table: `products`
- `id`: `Integer`, Primary Key, Autoincrement.
- `category_id`: `Integer`, ForeignKey(`product_categories.id`), Index.
- `name`: `String(255)`, Not Null.
- `slug`: `String(255)`, Unique, Index.
- `description`: `Text`, Not Null.
- `image_url`: `String(512)`, Nullable.
- `delivery_type`: `Enum('AUTO_SERIAL', 'AUTO_ACCOUNT', 'LICENSE_KEY', 'MANUAL')`, Default `'AUTO_SERIAL'`.
- `is_active`: `Boolean`, Default `True`, Index.
- `is_trial_or_email`: `Boolean`, Default `False`, Index.
- `created_at`: `DateTime(timezone=True)`, ServerDefault `now()`.

#### Table: `product_variants`
- `id`: `Integer`, Primary Key, Autoincrement.
- `product_id`: `Integer`, ForeignKey(`products.id`, ondelete='CASCADE'), Index.
- `name`: `String(100)`, Not Null (e.g., "1 Month", "18 Month Access", "Private Account").
- `price`: `Numeric(10, 2)`, Not Null.
- `display_order`: `Integer`, Default `0`.
- `is_active`: `Boolean`, Default `True`, Index.

#### Table: `inventory_items`
- `id`: `UUID`, Primary Key, Default `gen_random_uuid()`.
- `product_id`: `Integer`, ForeignKey(`products.id`), Index.
- `variant_id`: `Integer`, ForeignKey(`product_variants.id`), Index.
- `payload`: `Text`, Not Null (Encrypted credentials, license key, or delivery text).
- `status`: `Enum('AVAILABLE', 'RESERVED', 'SOLD', 'EXPIRED', 'DISABLED')`, Default `'AVAILABLE'`, Index.
- `order_id`: `UUID`, ForeignKey(`orders.id`), Nullable, Index.
- `reserved_at`: `DateTime(timezone=True)`, Nullable.
- `sold_at`: `DateTime(timezone=True)`, Nullable.
- `created_at`: `DateTime(timezone=True)`, ServerDefault `now()`.
- *Indexes*: Composite index on `(variant_id, status)` for lightning-fast stock checks and locking.

#### Table: `orders`
- `id`: `UUID`, Primary Key, Default `gen_random_uuid()`.
- `order_number`: `String(32)`, Unique, Index (e.g. `ORD-20260908-4F2A`).
- `user_id`: `BigInteger`, ForeignKey(`users.id`), Index.
- `status`: `Enum('PENDING', 'PROCESSING', 'COMPLETED', 'CANCELLED', 'REFUNDED', 'FAILED')`, Default `'PENDING'`, Index.
- `total_amount`: `Numeric(10, 2)`, Not Null.
- `currency`: `String(3)`, Default `'USD'`.
- `payment_method`: `Enum('WALLET', 'TELEGRAM_STARS', 'CRYPTO', 'EXTERNAL_GATEWAY')`, Default `'WALLET'`.
- `delivery_content`: `Text`, Nullable (Cached delivery text sent to the user).
- `ip_address`: `String(45)`, Nullable.
- `created_at`: `DateTime(timezone=True)`, ServerDefault `now()`.
- `completed_at`: `DateTime(timezone=True)`, Nullable.

#### Table: `order_items`
- `id`: `UUID`, Primary Key, Default `gen_random_uuid()`.
- `order_id`: `UUID`, ForeignKey(`orders.id`, ondelete='CASCADE'), Index.
- `product_id`: `Integer`, ForeignKey(`products.id`), Index.
- `variant_id`: `Integer`, ForeignKey(`product_variants.id`), Index.
- `inventory_item_id`: `UUID`, ForeignKey(`inventory_items.id`), Nullable, Index.
- `price`: `Numeric(10, 2)`, Not Null.
- `quantity`: `Integer`, Default `1`.

#### Table: `referrals`
- `id`: `UUID`, Primary Key, Default `gen_random_uuid()`.
- `referrer_id`: `BigInteger`, ForeignKey(`users.id`), Index.
- `referee_id`: `BigInteger`, ForeignKey(`users.id`), Unique, Index.
- `commission_rate`: `Numeric(5, 2)`, Default `10.00` (10%).
- `total_commission_earned`: `Numeric(10, 2)`, Default `0.00`.
- `created_at`: `DateTime(timezone=True)`, ServerDefault `now()`.

#### Table: `referral_transactions`
- `id`: `UUID`, Primary Key, Default `gen_random_uuid()`.
- `referrer_id`: `BigInteger`, ForeignKey(`users.id`), Index.
- `referee_id`: `BigInteger`, ForeignKey(`users.id`), Index.
- `order_id`: `UUID`, ForeignKey(`orders.id`), Index.
- `order_amount`: `Numeric(10, 2)`, Not Null.
- `commission_amount`: `Numeric(10, 2)`, Not Null.
- `status`: `Enum('PENDING', 'PAID', 'CANCELLED')`, Default `'PAID'`.
- `created_at`: `DateTime(timezone=True)`, ServerDefault `now()`.

#### Table: `referral_rewards` (Referral Store)
- `id`: `Integer`, Primary Key, Autoincrement.
- `title`: `String(255)`, Not Null.
- `required_referrals`: `Integer`, Not Null (e.g. 10, 50, 100).
- `reward_type`: `Enum('WALLET_CREDIT', 'PRODUCT_VARIANT', 'COUPON')`, Not Null.
- `reward_value`: `String(255)`, Not Null (e.g. amount or product_variant_id).
- `is_active`: `Boolean`, Default `True`.

#### Table: `referral_redemptions`
- `id`: `UUID`, Primary Key, Default `gen_random_uuid()`.
- `user_id`: `BigInteger`, ForeignKey(`users.id`), Index.
- `reward_id`: `Integer`, ForeignKey(`referral_rewards.id`), Index.
- `created_at`: `DateTime(timezone=True)`, ServerDefault `now()`.

#### Table: `freebies` & `freebie_claims`
- `freebies`: `id`, `title`, `description`, `reward_type`, `reward_value`, `cooldown_hours` (e.g. 24h), `stock_limit`, `claimed_count`, `is_active`, `expires_at`.
- `freebie_claims`: `id`, `freebie_id`, `user_id`, `created_at`, Index on `(freebie_id, user_id, created_at)`.

#### Table: `coupons` & `coupon_redemptions`
- `coupons`: `id`, `code` (Unique), `discount_type` ('PERCENTAGE', 'FIXED'), `discount_value`, `min_order_amount`, `max_uses`, `current_uses`, `is_active`, `expires_at`.
- `coupon_redemptions`: `id`, `coupon_id`, `user_id`, `order_id`, `discount_applied`, `redeemed_at`.

#### Table: `support_tickets` & `ticket_messages`
- `support_tickets`: `id` (UUID), `ticket_number` (`TICK-1001`), `user_id`, `category` ('PAYMENT', 'ORDER', 'ACCOUNT', 'OTHER'), `subject`, `status` ('OPEN', 'IN_PROGRESS', 'RESOLVED', 'CLOSED'), `created_at`, `updated_at`.
- `ticket_messages`: `id`, `ticket_id`, `sender_type` ('USER', 'ADMIN', 'SYSTEM'), `sender_id`, `message_text`, `created_at`.

#### Table: `membership_channels`
- `id`: `Integer`, Primary Key, Autoincrement.
- `title`: `String(255)`, Not Null.
- `channel_id`: `BigInteger`, Not Null, Unique (Telegram Chat ID, e.g. `-100123456789`).
- `invite_link`: `String(255)`, Not Null.
- `is_mandatory`: `Boolean`, Default `True`.
- `is_active`: `Boolean`, Default `True`.

#### Table: `api_keys` & `api_usage` (Reseller Platform)
- `api_keys`: `id` (UUID), `user_id`, `key_prefix` (`qam_live_...`), `key_hash` (Argon2 / SHA256), `is_active`, `rate_limit_rpm` (Default 60), `allowed_ips` (Array or JSON), `created_at`, `last_used_at`.
- `api_usage`: `id`, `api_key_id`, `endpoint`, `status_code`, `response_time_ms`, `ip_address`, `created_at`.

#### Table: `audit_logs` & `settings`
- `audit_logs`: `id`, `admin_id`, `action`, `target_type`, `target_id`, `old_values` (JSONB), `new_values` (JSONB), `ip_address`, `created_at`.
- `settings`: `key` (`String(100)`, PK), `value` (JSONB), `description`, `updated_at`.

---

## 4. Key Architectural Subsystems

### 4.1 Mandatory Membership Gate Pipeline

```
User triggers /start [ref_CODE]
          │
          ▼
Middleware: Upsert user record (record referrer if new and valid)
          │
          ▼
Check configured mandatory channels (membership_channels table)
          │
  ┌───────┴───────┐
  ▼               ▼
All joined?     Missing >= 1 channel/group
  │               │
  │               ▼
  │       Render Gate Screen:
  │       - 📢 Join Channel [Link]
  │       - 👥 Join Group [Link]
  │       - ✅ I have joined [callback: verify_membership]
  │
  ▼
On ✅ I have joined callback:
  Invoke Telegram Bot API: get_chat_member(chat_id, user_id)
  Verify status in ('member', 'administrator', 'creator')
  If all confirmed:
    Send alert popup: "✅ Verified — welcome!"
    Delete/Edit Gate message -> Render Main Dashboard Menu
  If not confirmed:
    Send alert popup: "❌ You have not joined all required channels yet!"
```

### 4.2 Concurrency & Atomic Purchase Engine

Preventing double-spending of wallet balance and race conditions on limited inventory (e.g. only 1 license key left):

```python
# Atomic purchase transaction in OrderService
async with db.begin():
    # 1. Lock user's wallet with row-level lock
    wallet = await db.execute(
        select(Wallet)
        .where(Wallet.user_id == user_id)
        .with_for_update()
    ).scalar_one()

    # 2. Check sufficient balance
    if wallet.balance < total_amount:
        raise InsufficientBalanceException("Wallet balance insufficient.")

    # 3. Find and Lock available inventory items using SKIP LOCKED
    stock_items = (await db.execute(
        select(InventoryItem)
        .where(
            InventoryItem.variant_id == variant_id,
            InventoryItem.status == InventoryStatus.AVAILABLE
        )
        .limit(quantity)
        .with_for_update(skip_locked=True)
    )).scalars().all()

    if len(stock_items) < quantity:
        raise OutOfStockException("Item was just claimed or is out of stock.")

    # 4. Create Order Record
    order = Order(
        user_id=user_id,
        status=OrderStatus.COMPLETED,
        total_amount=total_amount,
        ...
    )
    db.add(order)
    await db.flush()

    # 5. Transition stock items to SOLD and bind to order
    delivery_lines = []
    for item in stock_items:
        item.status = InventoryStatus.SOLD
        item.order_id = order.id
        item.sold_at = func.now()
        delivery_lines.append(item.payload)

    # 6. Deduct balance and create immutable transaction log
    balance_before = wallet.balance
    wallet.balance -= total_amount
    wallet.total_spent += total_amount

    tx = WalletTransaction(
        wallet_id=wallet.id,
        user_id=user_id,
        type=TransactionType.ORDER_PAYMENT,
        amount=-total_amount,
        balance_before=balance_before,
        balance_after=wallet.balance,
        reference_id=str(order.id),
        description=f"Purchase order {order.order_number}"
    )
    db.add(tx)

    # 7. Referral commission processing
    await referral_service.process_order_commission(db, order)

# Delivery message is sent via Telegram only AFTER transaction successfully commits!
```

### 4.3 Referral Deep-Linking & Anti-Abuse Rules

1. **Deep Link Format**: `https://t.me/<bot_username>?start=ref_<UNIQUE_CODE>`
2. **Validation**:
   - New user only: `user.created_at` within 10 seconds of referral attribution. Existing users cannot be retroactively referred.
   - Self-referral prevention: `referrer_id != referee_id`.
   - Cycle prevention: A cannot refer B if B referred A.
   - Idempotent attribution: Once a referee has a `referred_by_id`, it is immutable.
3. **Commission Trigger**: Commission is only credited when the referee completes a valid non-refunded purchase.

### 4.4 Live Sales Channel Notification Service (as seen in Screenshot 2)

Whenever an order completes or a freebie is claimed:
1. `NotificationService` formats an anonymized broadcast card:
   - `User J***** just bought 1x 🇬 Gemini AI Pro 18 Month!`
   - Attached button: `[Gemini AI Pro 18 Month ↗]` (deep links directly to the product in the bot).
2. Dispatches asynchronously to the public updates group/channel configured in settings.

---

## 5. Security & Threat Modeling

| Threat Vector | Potential Impact | Architecture Mitigation |
|---|---|---|
| **Bot Token Compromise** | Complete takeover of bot and user communication | Stored strictly in environment variables; zero hardcoding; `.env` omitted from git; rotation support. |
| **Race Condition on Stock / Wallet** | Users double-claiming items or balance going negative | PostgreSQL `with_for_update()` row-level locks, `CHECK (balance >= 0.00)` DB constraint, and `skip_locked=True`. |
| **Tampered Callback Queries** | User forging user ID or price in inline keyboards | `callback_data` holds only opaque item IDs and action tokens; user identity is derived strictly from `event.from_user.id` authenticated by Telegram. |
| **Referral Gaming / Sybil Attack** | Creating spam accounts to claim referral payouts | Commission paid only on actual completed purchases; minimum withdrawal / spend requirements; rate limiting on new account creation. |
| **Reseller API Flooding / Key Theft** | Denial of service / draining reseller balance | API keys stored as SHA-256 hashes; Redis-backed token bucket rate limiting (60 RPM default); optional IP whitelist. |
| **Telegram Broadcast Rate Limits** | Bot blocked or banned by Telegram for spamming | Token-bucket throttling middleware (max 30 msgs/sec global, max 1 msg/sec per user) using asyncio queues and exponential backoff. |

---

## 6. Phased Implementation Roadmap

- **Phase 1: Project & Architecture Foundation**
  - Directory structure, pyproject/requirements, `.env.example`, Pydantic Settings, Async SQLAlchemy engine, logging.
- **Phase 2: Database Models & Migrations**
  - Models for User, Wallet, Product, Inventory, Order, Referral, Freebie, Coupon, Support.
  - Initial Alembic migration and repository layer.
- **Phase 3: Telegram Bot Core & Membership Gate**
  - aiogram 3.x Dispatcher, Router structure, error handling.
  - `/start` handler with deep linking (`ref_...`), mandatory channel membership check, verification callback.
- **Phase 4: Main Navigation UI & Profile**
  - Dynamic main menu with user stats (Balance, Total Spent, Referrals, Tier).
  - Profile view, Clear Chat handler, reusable inline keyboard builders.
- **Phase 5: Catalog & Shop System**
  - Category browsing, Product selection, Variants, Dynamic Stock counters, Pagination.
- **Phase 6: Inventory & Concurrency-Safe Order Engine**
  - Atomic stock reservation (`SELECT ... FOR UPDATE SKIP LOCKED`), order state machine, instant digital delivery.
- **Phase 7: Immutable Wallet System**
  - Wallet balance queries, manual deposit vouchers/codes, transaction history, strict balance audit logging.
- **Phase 8: Referral System & Referral Store**
  - Deep-link attribution, commission settlement, tiered milestone rewards (10/50/100 referrals).
- **Phase 9: Freebies & Coupons**
  - Cooldown-enforced daily freebies, coupon discount validation on checkout.
- **Phase 10: Support Ticket System**
  - Ticket submission flow via FSM, admin forwarding and bi-directional reply bridge.
- **Phase 11: Notification & Live Channel Broadcasts**
  - Async event emitter for real-time buyer announcements into the community group.
- **Phase 12: Reseller REST API**
  - FastAPI endpoints for products, stock checks, and programmatic order execution with API key auth.
- **Phase 13: Web Admin Dashboard**
  - FastAPI + Jinja2/Tailwind dashboard for catalog, inventory, order management, and user lookups.
- **Phase 14: Payment Gateway Integration**
  - Telegram Stars and external crypto/fiat payment webhook processors with idempotency verification.
- **Phase 15: Security Hardening, Automated Testing & Deployment**
  - Comprehensive pytest suite (unit, integration, concurrency), Docker Compose configuration, Nginx setup.

---

## 7. Testing & Verification Strategy

1. **Unit Tests**:
   - `test_models.py`: Database table constraints, foreign key cascades, non-negative checks.
   - `test_wallet_service.py`: Exact deposit/debit balance arithmetic, transaction logging correctness.
   - `test_coupon_service.py`: Percentage vs fixed discount calculations, expiration, usage limits.
2. **Concurrency Tests**:
   - `test_inventory_concurrency.py`: Launch 20 concurrent tasks attempting to buy a single remaining inventory item. Verify exactly 1 succeeds and 19 receive `OutOfStockException`.
3. **Bot Handler Tests**:
   - Mock aiogram `Message` and `CallbackQuery` objects.
   - Test membership gate verification logic with mocked `get_chat_member` returns (`member` vs `left`).
4. **API Integration Tests**:
   - Test Reseller API authentication, rate limiting, and order placement via `httpx.AsyncClient`.
