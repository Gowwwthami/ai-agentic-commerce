from sqlalchemy import String, Text, Numeric, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    asin: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    brand: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    price: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="INR"
    )

    rating: Mapped[float | None] = mapped_column(
        Numeric(2, 1),
        nullable=True
    )

    review_count: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    image_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    inventory: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    merchant: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="GlowCart"
    )

    available: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )

class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    asin: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True
    )

    rating: Mapped[float] = mapped_column(
        Numeric(2, 1),
        nullable=False
    )

    review_text: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )