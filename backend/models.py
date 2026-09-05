from datetime import datetime

from sqlalchemy import String, Text, Numeric, Integer, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    asin: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    brand: Mapped[str | None] = mapped_column(String(100), nullable=True)

    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")

    rating: Mapped[float | None] = mapped_column(Numeric(2, 1), nullable=True)

    review_count: Mapped[int] = mapped_column(Integer, default=0)

    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    inventory: Mapped[int] = mapped_column(Integer, default=0)

    merchant: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="GlowCart",
    )

    available: Mapped[bool] = mapped_column(Boolean, default=True)


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    asin: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    rating: Mapped[float] = mapped_column(Numeric(2, 1), nullable=False)

    review_text: Mapped[str] = mapped_column(Text, nullable=False)


class ShoppingSession(Base):
    __tablename__ = "shopping_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    conversation: Mapped[str] = mapped_column(Text, nullable=False, default="[]")

    last_product_ids: Mapped[str] = mapped_column(Text, nullable=False, default="[]")

    recommended_product_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    active_order_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    last_comparison_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class CartItem(Base):
    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("shopping_sessions.id"),
        nullable=False,
        index=True,
    )

    product_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("products.id"),
        nullable=False,
    )

    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    unit_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("shopping_sessions.id"),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="CART")

    total_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")

    merchant: Mapped[str] = mapped_column(String(100), nullable=False)

    items_snapshot: Mapped[str] = mapped_column(Text, nullable=False, default="[]")

    razorpay_order_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    razorpay_payment_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    payment_link_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    payment_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    session_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)

    order_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    description: Mapped[str] = mapped_column(Text, nullable=False)

    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
