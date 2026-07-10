"""Payments router."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.lenco_client import LencoClient
from app.config import settings
from app.dependencies import get_db
from app.repositories.booking_repo import BookingRepository
from app.repositories.notification_repo import NotificationRepository
from app.repositories.payment_repo import PaymentRepository
from app.schemas.common import envelope
from app.schemas.payment import MobileMoneyPaymentRequest
from app.services.payment_service import PaymentService

router = APIRouter()
webhook_router = APIRouter()


def _service(db: AsyncSession) -> PaymentService:
    return PaymentService(
        PaymentRepository(db),
        LencoClient(settings),
        BookingRepository(db),
        NotificationRepository(db),
    )


@router.post("/lenco/mobile-money")
async def initiate_mobile_money(
    body: MobileMoneyPaymentRequest, db: AsyncSession = Depends(get_db)
) -> dict:
    payment = await _service(db).initiate_mobile_money_payment(body)
    return envelope(True, "Payment initiated", payment)


@router.get("/lenco/{reference}")
async def get_lenco_payment(
    reference: str, db: AsyncSession = Depends(get_db)
) -> dict:
    payment = await _service(db).get_payment_status(reference)
    return envelope(True, "Payment retrieved", payment)


@webhook_router.post("/lenco")
async def lenco_webhook(
    request: Request, db: AsyncSession = Depends(get_db)
) -> dict:
    payload = await request.body()
    signature = request.headers.get("X-Lenco-Signature")
    await _service(db).process_webhook(payload, signature)
    return envelope(True, "Received", None)
