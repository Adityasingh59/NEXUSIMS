# NEXUS IMS

**Rigid Accuracy. Infinite Flexibility.**

Inventory Management System — Block 0 (Foundation) and Block 1 (SKU & Item Types) implementation.

## Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy (async), Alembic, PostgreSQL 16, Redis 7, Celery 5
- **Frontend**: React 18, Vite, Zustand, React Query, Axios
- **Infra**: Docker Compose, nginx

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 20+ (for local frontend dev)
- Python 3.12 (for local backend dev)

### Run with Docker

```bash
# Copy env
cp backend/.env.example backend/.env

# Start all services
docker compose up -d

# Run migrations (first time)
docker compose exec fastapi alembic upgrade head
```

- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/api/v1/docs
- **Health**: http://localhost:8000/health

### Local Development

**Backend:**
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Ensure Postgres & Redis running (or use Docker for DB only)
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

### Linting

```bash
# Backend
cd backend && ruff check . && black --check .

# Frontend
cd frontend && npm run lint
```

## Project Structure

```
├── backend/           # FastAPI app
│   ├── app/
│   │   ├── api/       # Routes, deps
│   │   ├── core/      # Security, auth, tenant
│   │   ├── db/        # Session, engine
│   │   ├── models/    # SQLAlchemy models
│   │   └── tasks/     # Celery tasks
│   ├── alembic/       # Migrations
│   └── scripts/       # Init SQL
├── frontend/          # React + Vite
├── nginx/
├── docker-compose.yml
└── .github/workflows/ # CI
```

## Block 0 Checklist

- [x] Monorepo layout (backend, frontend)
- [x] Docker Compose (postgres, redis, fastapi, celery-worker, celery-beat, nginx)
- [x] FastAPI skeleton, Uvicorn, Alembic, pydantic-settings
- [x] React 18 + Vite, Zustand, React Query, Axios, PWA manifest
- [x] PostgreSQL 16, nexus_app / nexus_admin roles
- [x] Alembic async, migration 0001 (tenants, users, user_roles)
- [x] RLS policies on tenant-scoped tables
- [x] JWT auth (python-jose), bcrypt, POST /auth/login, /auth/refresh, /auth/logout, GET /auth/me
- [x] Tenant context middleware, SET app.tenant_id for RLS
- [x] Redis, Celery 5, base task patterns
- [x] Ruff, black, ESLint, Prettier, pre-commit, CI

## Block 1 Checklist — SKU & Item Type Management

- [x] item_types table (tenant_id, name, code, attribute_schema JSONB, version, is_archived)
- [x] skus table (tenant_id, sku_code, name, item_type_id, attributes JSONB, reorder_point, unit_cost)
- [x] GIN index on skus.attributes for attribute-value filtering
- [x] ItemTypeService (create, update_schema, get_item_types, archive)
- [x] SKUService (create, update, get_skus, search with filters, archive)
- [x] Attribute validation against item_type.attribute_schema
- [x] API: GET/POST /item-types, GET/PUT/DELETE /item-types/{id}
- [x] API: GET/POST /skus, GET/PUT/DELETE /skus/{id} (with filters: item_type_id, search, low_stock)
- [x] Response envelope {data, error, meta} with pagination
- [x] Frontend: Item Type builder, SKU list view, SKU create form (dynamic attributes)

## Block 2 Checklist — Stock Ledger & Transactions

- [x] warehouses table (minimal: id, tenant_id, name, code, is_active)
- [x] stock_ledger table (append-only, event_type ENUM)
- [x] GIN indexes, INSERT-only REVOKE for nexus_app
- [x] Negative stock trigger (check_negative_stock)
- [x] LedgerService.post_event(), get_stock_level() (Redis cache-aside, 30s TTL)
- [x] LedgerService.get_transaction_history() with running balance
- [x] API: POST /transactions/receive, /pick, /adjust, /return
- [x] API: GET /transactions (filtered), GET /transactions/stock
- [x] API: POST /cycle-counts/submit, /cycle-counts/commit
- [x] API: GET/POST /warehouses
- [x] API: GET /warehouses/{id}/stock, PUT /warehouses/{id}

## Block 3 Checklist — Multi-Warehouse & Locations

- [x] locations table (warehouse_id, parent_id, name, code, location_type ZONE|AISLE|BIN)
- [x] transfer_orders table (from_warehouse_id, to_warehouse_id, status PENDING|IN_TRANSIT|RECEIVED|CANCELLED)
- [x] transfer_order_lines table (sku_id, quantity_requested, quantity_received)
- [x] LocationService (CRUD, get_location_path)
- [x] TransferService (create_transfer_order, confirm_receipt, cancel_transfer_order)
- [x] TRANSFER_OUT on create, TRANSFER_IN on receipt (atomic ledger events)
- [x] API: GET/POST /locations, GET /locations/{id}/path
- [x] API: POST /transfers, GET /transfers, POST /transfers/{id}/receive, POST /transfers/{id}/cancel
- [x] Frontend: Locations hierarchy builder, Transfer order flow, Warehouse context switcher

## Block 4 Checklist — User Roles & RBAC

- [x] `roles` table (id, name, permissions JSONB)
- [x] `user_roles` mapping table
- [x] Auth middleware checking permissions array
- [x] `api_keys` table for programmatic access
- [x] `audit_logs` table (user_id, action, entity, entity_id, changes JSONB)
- [x] API: GET/POST `/users`, GET/POST/DELETE `/api-keys`
- [x] Frontend: Users & API Keys dashboards

## Block 5 Checklist — Barcode Scanning MVP

- [x] `scan_lookup(barcode, warehouse)` API unifying SKU & UUID lookup
- [x] `scan_receive` / `scan_pick` endpoints for quick stock movements
- [x] `scan_adjust` endpoint with reason codes
- [x] Frontend: Dedicated Scanner UI dashboard with Receive/Pick/Adjust modes
- [x] Success/Error overlays and enter-to-submit workflow

## Block 6 Checklist — Reporting & Dashboards

- [x] `cogs_service` calculating generic inventory value via last-known unit cost
- [x] Dashboard API: `total_stock_value`, `low_stock_count`, `recent_activity`
- [x] Live Inventory Valuation report query
- [x] Operations/Movement History query
- [x] Frontend: Dashboard metrics view and comprehensive Reports page

## Block 7 Checklist — Assembly & Kitting (BOM Engine)

- [x] `boms` and `bom_lines` tables (with versioning, landed cost)
- [x] `assembly_orders` table (planned, produced, waste)
- [x] `stock_ledger` ENUM expanded (`ASSEMBLE_OUT`, `ASSEMBLE_IN`)
- [x] `AssemblyService` (create_bom, check_availability, start, complete order)
- [x] COGS recorded dynamically based on components + BOM overhead
- [x] API: `/boms`, `/assembly-orders`
- [x] Frontend: BOMs builder, stock availability simulator, Assembly execution dashboard

## Block 8 Checklist — Order Fulfillment & Shipping

- [ ] `sales_orders` and `sales_order_lines` tables
- [ ] `stock_ledger` ENUM expanded (`SHIP_OUT`, `RESERVE_OUT`, `RESERVE_IN`)
- [ ] `FulfillmentService` (allocate_stock, ship_order)
- [ ] API: `/sales-orders`
- [ ] Frontend: SalesOrders dashboard with soft-allocation and physical shipping flows
