"""Payments router."""

from fastapi import APIRouter, Depends, Request
from app.dependencies import StudentUser
from app.providers import get_payment_service
from app.schemas.common import Envelope, envelope
from app.schemas.payment import (
    CardPaymentRequest,
    MobileMoneyPaymentRequest,
    PaymentResponse,
)
from app.services.payment_service import PaymentService

router = APIRouter()
webhook_router = APIRouter()


@router.post("/lenco/mobile-money", response_model=Envelope[PaymentResponse])
async def initiate_mobile_money(
    body: MobileMoneyPaymentRequest,
    current_user: StudentUser,
    service: PaymentService = Depends(get_payment_service),
) -> dict:
    payment = await service.initiate_mobile_money_payment(
        body, user_id=current_user.id
    )
    return envelope(True, "Payment initiated", payment)


@router.post("/lenco/card", response_model=Envelope[PaymentResponse])
async def initiate_card(
    body: CardPaymentRequest,
    current_user: StudentUser,
    service: PaymentService = Depends(get_payment_service),
) -> dict:
    payment = await service.initiate_card_payment(
        body, user_id=current_user.id
    )
    return envelope(True, "Card payment initiated", payment)


@router.get("/lenco/{reference}", response_model=Envelope[PaymentResponse])
async def get_lenco_payment(
    reference: str,
    current_user: StudentUser,
    service: PaymentService = Depends(get_payment_service),
) -> dict:
    payment = await service.get_payment_status(
        reference, user_id=current_user.id
    )
    return envelope(True, "Payment retrieved", payment)


@webhook_router.post("/lenco")
async def lenco_webhook(
    request: Request,
    service: PaymentService = Depends(get_payment_service),
) -> dict:
    """Receive a Lenco webhook and reconcile payment status."""
    payload = await request.body()
    signature = request.headers.get("X-Lenco-Signature")
    await service.process_webhook(payload, signature)
    return envelope(True, "Received", None)
