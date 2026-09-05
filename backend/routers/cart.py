"""Cart CRUD router — delegates entirely to cart_service."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from deps import get_db
from schemas import CartAddRequest, CartUpdateRequest
from services.cart_service import (
    add_to_cart,
    get_cart,
    remove_from_cart,
    update_cart_item,
)
from services.session_service import get_or_create_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/cart", tags=["Cart"])


@router.get("/{session_id}")
def get_cart_endpoint(session_id: str, db: Session = Depends(get_db)):
    """Return the current cart for a session."""
    return get_cart(db, session_id)


@router.post("/add")
def add_item(payload: CartAddRequest, db: Session = Depends(get_db)):
    """Add a product to the cart.  Returns the updated Cart."""
    # Ensure session exists before inserting cart item (FK constraint)
    get_or_create_session(db, payload.session_id)
    return add_to_cart(
        db,
        payload.session_id,
        payload.product_id,
        payload.quantity,
    )


@router.patch("/items/{item_id}")
def update_item(
    item_id: int,
    payload: CartUpdateRequest,
    db: Session = Depends(get_db),
):
    """Update the quantity of a cart item.  Returns the updated Cart."""
    return update_cart_item(db, payload.session_id, item_id, payload.quantity)


@router.delete("/items/{item_id}")
def remove_item(
    item_id: int,
    session_id: str,
    db: Session = Depends(get_db),
):
    """Remove a cart item.  Returns the updated Cart."""
    return remove_from_cart(db, session_id, item_id)
