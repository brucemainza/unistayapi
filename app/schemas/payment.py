"""Schemas for Lenco mobile-money payments."""

from pydantic import BaseModel, Field


class MobileMoneyPaymentRequest(BaseModel):
    amount: str = Field(..., pattern=r"^\d+(\.\d{1,2})?$")
    phone: str = Field(..., min_length=9, max_length=20)
    operator: str = Field(..., pattern=r"^(airtel|mtn|zamtel)$")
    booking_id: str | None = None
    currency: str = Field(default="ZMW", min_length=3, max_length=3)
    country: str = Field(default="zm", pattern=r"^(zm|mw)$")


class PaymentResponse(BaseModel):
    reference: str
    status: str
    amount: str
    currency: str
    lencoReference: str | None = None
