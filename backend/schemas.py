from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=64)
    message: str = Field(min_length=1, max_length=2000)


class CartAddRequest(BaseModel):
    session_id: str
    product_id: int
    quantity: int = Field(default=1, ge=1, le=20)


class CartUpdateRequest(BaseModel):
    session_id: str
    quantity: int = Field(ge=0, le=20)


class SessionRequest(BaseModel):
    session_id: str


class CheckoutConfirmRequest(BaseModel):
    session_id: str
    confirm: bool = False


class PaymentVerifyRequest(BaseModel):
    session_id: str
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class PaymentActionRequest(BaseModel):
    session_id: str
