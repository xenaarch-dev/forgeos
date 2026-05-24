from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import CurrentUserDep
from ..db import get_session
from ..models import Item
from ..rate_limit import RateLimitDep
from ..schemas import ItemCreate, ItemRead, ItemUpdate

router = APIRouter(prefix="/items", tags=["items"])


@router.get("", response_model=list[ItemRead])
async def list_items(
    user: CurrentUserDep,
    session: AsyncSession = Depends(get_session),
) -> list[ItemRead]:
    rows = await session.scalars(
        select(Item).where(Item.user_id == uuid.UUID(user.sub)).order_by(Item.created_at.desc())
    )
    return [ItemRead.model_validate(r) for r in rows]


@router.post("", response_model=ItemRead, status_code=status.HTTP_201_CREATED)
async def create_item(
    payload: ItemCreate,
    user: CurrentUserDep,
    _: RateLimitDep,
    session: AsyncSession = Depends(get_session),
) -> ItemRead:
    item = Item(user_id=uuid.UUID(user.sub), title=payload.title, data=payload.data)
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return ItemRead.model_validate(item)


@router.patch("/{item_id}", response_model=ItemRead)
async def update_item(
    item_id: uuid.UUID,
    payload: ItemUpdate,
    user: CurrentUserDep,
    _: RateLimitDep,
    session: AsyncSession = Depends(get_session),
) -> ItemRead:
    item = await session.get(Item, item_id)
    if not item or item.user_id != uuid.UUID(user.sub):
        raise HTTPException(status_code=404, detail="Item not found")
    if payload.title is not None:
        item.title = payload.title
    if payload.data is not None:
        item.data = payload.data
    await session.commit()
    await session.refresh(item)
    return ItemRead.model_validate(item)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: uuid.UUID,
    user: CurrentUserDep,
    _: RateLimitDep,
    session: AsyncSession = Depends(get_session),
) -> None:
    item = await session.get(Item, item_id)
    if not item or item.user_id != uuid.UUID(user.sub):
        raise HTTPException(status_code=404, detail="Item not found")
    await session.delete(item)
    await session.commit()
