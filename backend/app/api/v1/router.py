"""NEXUS IMS — API v1 router aggregation."""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    api_keys,
    auth,
    boms,
    cogs,
    cycle_counts,
    item_types,
    locations,
    purchase_orders,
    reports,
    scan,
    skus,
    transactions,
    transfers,
    users,
    warehouses,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(api_keys.router, prefix="/api-keys", tags=["api-keys"])
api_router.include_router(item_types.router, prefix="/item-types", tags=["item-types"])
api_router.include_router(skus.router, prefix="/skus", tags=["skus"])
api_router.include_router(warehouses.router, prefix="/warehouses", tags=["warehouses"])
api_router.include_router(locations.router, prefix="/locations", tags=["locations"])
api_router.include_router(transfers.router, prefix="/transfers", tags=["transfers"])
api_router.include_router(transactions.router, prefix="/transactions", tags=["transactions"])
api_router.include_router(cycle_counts.router, prefix="/cycle-counts", tags=["cycle-counts"])
api_router.include_router(boms.router, prefix="/boms", tags=["boms"])
api_router.include_router(purchase_orders.router, prefix="/purchase-orders", tags=["purchase-orders"])
api_router.include_router(cogs.router, prefix="/cogs", tags=["cogs"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(scan.router, prefix="/scan", tags=["scanner"])
