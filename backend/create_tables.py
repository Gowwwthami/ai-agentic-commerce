from database import engine, Base
from models import (  # noqa: F401 — register metadata
    Product,
    Review,
    ShoppingSession,
    CartItem,
    Order,
    AuditEvent,
)

print("Creating database tables...")

Base.metadata.create_all(bind=engine)

print("Tables created successfully!")
