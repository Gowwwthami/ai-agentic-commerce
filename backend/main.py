import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import router
from routers.chat import router as chat_router
from routers.cart import router as cart_router
from routers.checkout import router as checkout_router
from routers.payment import router as payment_router
from routers.audit import router as audit_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)

app = FastAPI(
    title="GlowCart — AI Shopping Agent",
    version="1.0.0",
    description=(
        "AI-powered conversational shopping agent with "
        "recommendations, review intelligence, "
        "and bounded Razorpay Test Mode checkout."
    ),
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Existing products / reviews routes
app.include_router(router)

# Chat and session
app.include_router(chat_router)

# Cart CRUD
app.include_router(cart_router)

# Checkout flow
app.include_router(checkout_router)

# Payment (verify, link, failed, key)
app.include_router(payment_router)

# Audit trail
app.include_router(audit_router)


@app.get("/")
def root():
    return {
        "message": "GlowCart AI Shopping Agent backend is running",
        "docs": "/docs",
    }
