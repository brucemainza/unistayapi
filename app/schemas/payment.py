"""Schemas for Lenco mobile-money and card payments."""

from pydantic import BaseModel, Field


class MobileMoneyPaymentRequest(BaseModel):
    amount: str = Field(..., pattern=r"^\d+(\.\d{1,2})?$")
    phone: str = Field(..., min_length=9, max_length=20)
    operator: str = Field(..., pattern=r"^(airtel|mtn|zamtel)$")
    booking_id: str | None = None
    currency: str = Field(default="ZMW", min_length=3, max_length=3)
    country: str = Field(default="zm", pattern=r"^(zm|mw)$")


class CustomerDetails(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)


class BillingAddress(BaseModel):
    street_address: str = Field(..., min_length=1, max_length=255)
    city: str = Field(..., min_length=1, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    postal_code: str = Field(..., min_length=1, max_length=20)
    country: str = Field(..., min_length=2, max_length=2)


class CardDetails(BaseModel):
    number: str = Field(..., min_length=13, max_length=19, pattern=r"^\d+$")
    expiry_month: str = Field(..., pattern=r"^(0[1-9]|1[0-2])$")
    expiry_year: str = Field(..., pattern=r"^\d{4}$")
    cvv: str = Field(..., min_length=3, max_length=4, pattern=r"^\d+$")


class CardPaymentRequest(BaseModel):
    amount: str = Field(..., pattern=r"^\d+(\.\d{1,2})?$")
    currency: str = Field(default="ZMW", min_length=3, max_length=3)
    email: str = Field(..., max_length=255)
    customer: CustomerDetails
    billing: BillingAddress
    card: CardDetails
    booking_id: str | None = None
    redirect_url: str | None = Field(default=None, max_length=500)


class PaymentResponse(BaseModel):
    reference: str
    status: str
    amount: str
    currency: str
    paymentType: str
    lencoReference: str | None = None
