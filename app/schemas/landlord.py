"""Schemas for landlord-specific operations."""

from pydantic import BaseModel, Field


class LandlordPaymentDetailRequest(BaseModel):
    bank_name: str | None = Field(default=None, max_length=100)
    account_name: str | None = Field(default=None, max_length=255)
    account_number: str | None = Field(default=None, max_length=50)
    mobile_money_provider: str | None = Field(default=None, max_length=50)
    mobile_money_number: str | None = Field(default=None, max_length=20)
    is_default: bool = True


class LandlordPaymentDetailResponse(BaseModel):
    id: str
    bankName: str | None
    accountName: str | None
    accountNumber: str | None
    mobileMoneyProvider: str | None
    mobileMoneyNumber: str | None
    isDefault: bool
