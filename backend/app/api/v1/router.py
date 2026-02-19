"""NEXUS IMS — API v1 router aggregation."""
from fastapi import APIRouter

from app.api.v1.endpoints import auth, cycle_counts, item_types, locations, skus, transactions, transfers, warehouses

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(item_types.router, prefix="/item-types", tags=["item-types"])
api_router.include_router(skus.router, prefix="/skus", tags=["skus"])
api_router.include_router(warehouses.router, prefix="/warehouses", tags=["warehouses"])
api_router.include_router(locations.router, prefix="/locations", tags=["locations"])
api_router.include_router(transfers.router, prefix="/transfers", tags=["transfers"])
api_router.include_router(transactions.router, prefix="/transactions", tags=["transactions"])
api_router.include_router(cycle_counts.router, prefix="/cycle-counts", tags=["cycle-counts"])
