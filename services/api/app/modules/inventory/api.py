"""REST API routes for inventory tracking, stock movements, and purchase orders."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.responses import Envelope, ok
from app.modules.auth.dependencies import CurrentPrincipal, require
from app.modules.auth.permissions import P
from app.modules.inventory.schemas import (
    InventoryItemCreate,
    InventoryItemOut,
    LowStockAlertOut,
    PurchaseOrderCreate,
    PurchaseOrderOut,
    StockMovementCreate,
    StockMovementOut,
)
from app.modules.inventory.service import InventoryService

router = APIRouter(prefix="/inventory", tags=["inventory"])


def get_service(session: Annotated[AsyncSession, Depends(get_session)]) -> InventoryService:
    return InventoryService(session)


@router.post("/items", response_model=Envelope[InventoryItemOut])
async def create_item(
    data: InventoryItemCreate,
    _: Annotated[CurrentPrincipal, Depends(require(P.INVENTORY_UPDATE))],
    service: Annotated[InventoryService, Depends(get_service)],
) -> Envelope[InventoryItemOut]:
    """Register a new consumable, reagent, or specimen container."""
    item = await service.create_item(data)
    return ok(item)  # type: ignore[arg-type]


@router.get("/items", response_model=Envelope[list[InventoryItemOut]])
async def list_items(
    _: Annotated[CurrentPrincipal, Depends(require(P.INVENTORY_VIEW))],
    service: Annotated[InventoryService, Depends(get_service)],
    category: str | None = Query(None),
    centre_id: uuid.UUID | None = Query(None),
) -> Envelope[list[InventoryItemOut]]:
    """List inventory items with stock levels."""
    items = await service.repo.list_items(category, centre_id)
    return ok(list(items))  # type: ignore[arg-type]


@router.post("/movements", response_model=Envelope[StockMovementOut])
async def record_movement(
    data: StockMovementCreate,
    principal: Annotated[CurrentPrincipal, Depends(require(P.INVENTORY_UPDATE))],
    service: Annotated[InventoryService, Depends(get_service)],
) -> Envelope[StockMovementOut]:
    """Record stock inflow, consumption, or manual adjustment."""
    movement = await service.record_movement(data, principal.user_id)
    return ok(movement)  # type: ignore[arg-type]


@router.get("/alerts", response_model=Envelope[list[LowStockAlertOut]])
async def get_low_stock_alerts(
    _: Annotated[CurrentPrincipal, Depends(require(P.INVENTORY_VIEW))],
    service: Annotated[InventoryService, Depends(get_service)],
) -> Envelope[list[LowStockAlertOut]]:
    """Get active alerts for items below reorder thresholds."""
    alerts = await service.get_low_stock_alerts()
    return ok(alerts)


@router.post("/purchase-orders", response_model=Envelope[PurchaseOrderOut])
async def create_purchase_order(
    data: PurchaseOrderCreate,
    _: Annotated[CurrentPrincipal, Depends(require(P.PURCHASE_MANAGE))],
    service: Annotated[InventoryService, Depends(get_service)],
) -> Envelope[PurchaseOrderOut]:
    """Create and submit a procurement purchase order."""
    po = await service.create_purchase_order(data)
    return ok(po)  # type: ignore[arg-type]


@router.get("/purchase-orders", response_model=Envelope[list[PurchaseOrderOut]])
async def list_purchase_orders(
    _: Annotated[CurrentPrincipal, Depends(require(P.INVENTORY_VIEW))],
    service: Annotated[InventoryService, Depends(get_service)],
    status: str | None = Query(None),
) -> Envelope[list[PurchaseOrderOut]]:
    """List procurement purchase orders."""
    items = await service.repo.list_purchase_orders(status)
    return ok(list(items))  # type: ignore[arg-type]


@router.post("/purchase-orders/{po_id}/receive", response_model=Envelope[PurchaseOrderOut])
async def receive_purchase_order(
    po_id: uuid.UUID,
    principal: Annotated[CurrentPrincipal, Depends(require(P.PURCHASE_MANAGE))],
    service: Annotated[InventoryService, Depends(get_service)],
) -> Envelope[PurchaseOrderOut]:
    """Acknowledge shipment arrival and credit items to stock."""
    po = await service.receive_purchase_order(po_id, principal.user_id)
    return ok(po)  # type: ignore[arg-type]
