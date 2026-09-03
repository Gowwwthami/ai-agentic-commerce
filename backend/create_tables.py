from database import engine, Base
from models import Product

print("Creating database tables...")

Base.metadata.create_all(bind=engine)

print("Tables created successfully!")