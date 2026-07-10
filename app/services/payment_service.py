"""Business logic for Lenco payments and webhooks."""

import hashlib
import hmac
import json
from decimal import Decimal
from uuid import uuid4

from app.clients.lenco_client import LencoClient
from app.config import settings
from app.exceptions import AuthError, NotFoundError, ValidationError
from app.models.notification import Notification
from app.models.payment import Payment
from app.repositories.booking_repo import BookingRepository
from app.repositories.notification_repo import NotificationRepository
from app.repositories.payment_repo import PaymentRepository
from app.schemas.payment import MobileMoneyPaymentRequest
from app.services.serializers import payment_to_dict


LENCO_TO_CLIENT_STATUS = {
    "pending": "pending",
    "processing": "processing",
    "pay-offline": "pay-offline",
    "successful": "successful",
    "completed": "successful",
    "failed": "failed",
    "cancelled": "failed",
}


class PaymentService:
    def __init__(
        self,
        payment_repo: PaymentRepository,
        lenco_client: LencoClient,
        booking_repo: BookingRepository | None = None,
        notification_repo: NotificationRepository | None = None,
    ) -> None:
        self.payment_repo = payment_repo
        self.lenco_client = lenco_client
        self.booking_repo = booking_repo
        self.notification_repo = notification_repo

    async def initiate_mobile_money_payment(
        self, request: MobileMoneyPaymentRequest
    ) -> dict:
        if request.booking_id and self.booking_repo is not None:
            booking = await self.booking_repo.get_by_id(request.booking_id)
            if booking is None:
                raise NotFoundError("Booking not found")

        reference = f"UNISTAY-{uuid4().hex[:18]}"
        payment = Payment(
            reference=reference,
            booking_id=request.booking_id,
            amount=Decimal(request.amount),
            currency=request.currency.upper(),
            operator=request.operator,
            phone=request.phone,
            status="pending",
            payload={},
        )
        payment = await self.payment_repo.create(payment)
        response = await self.lenco_client.charge_mobile_money(
            amount=request.amount,
            reference=reference,
            phone=request.phone,
            operator=request.operator,
            country=request.country,
        )
        data = response.get("data") or {}
        status = data.get("status") or "processing"
        payment = await self.payment_repo.update(
            payment,
            status=status,
            lenco_reference=data.get("lencoReference"),
            payload=response,
        )
        return payment_to_dict(payment)

    async def get_payment_status(self, reference: str) -> dict:
        payment = await self.payment_repo.get_by_reference(reference)
        if payment is None:
            raise NotFoundError("Payment not found")

        if not settings.lenco_mock and payment.status in {"pending", "processing", "pay-offline"}:
            response = await self.lenco_client.get_collection_status(reference)
            data = response.get("data") or {}
            status = data.get("status")
            if status:
                payment = await self.payment_repo.update(
                    payment,
                    status=status,
                    lenco_reference=data.get("lencoReference") or payment.lenco_reference,
                    payload=response,
                )
        return payment_to_dict(payment)

    async def process_webhook(self, payload: bytes, signature: str | None) -> None:
        if not self.verify_signature(payload, signature):
            raise AuthError("Invalid Lenco signature")
        try:
            event = json.loads(payload.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValidationError("Invalid webhook payload") from exc

        data = event.get("data") or {}
        reference = (
            data.get("reference")
            or data.get("clientReference")
            or data.get("transactionReference")
        )
        if not reference:
            return

        payment = await self.payment_repo.get_by_reference(reference)
        if payment is None:
            return

        event_name = event.get("event", "")
        status = data.get("status")
        if event_name.endswith(".successful") or status == "successful":
            status = "successful"
        elif event_name.endswith(".failed") or status == "failed":
            status = "failed"

        if status in LENCO_TO_CLIENT_STATUS:
            payment = await self.payment_repo.update(
                payment,
                status=LENCO_TO_CLIENT_STATUS[status],
                lenco_reference=data.get("lencoReference") or payment.lenco_reference,
                payload=event,
            )
            if status == "successful" and self.notification_repo and payment.booking:
                await self.notification_repo.create(
                    Notification(
                        user_id=payment.booking.student_id,
                        title="Payment successful",
                        body="Your accommodation payment was successful.",
                    )
                )

    @staticmethod
    def verify_signature(payload: bytes, signature: str | None) -> bool:
        if settings.lenco_mock and not signature:
            return True
        if not signature:
            return False

        secret = settings.lenco_webhook_secret or settings.lenco_api_key
        if not secret:
            return settings.environment != "production"

        candidates = []
        webhook_hash_key = hashlib.sha256(secret.encode("utf-8")).hexdigest()
        candidates.append(
            hmac.new(
                webhook_hash_key.encode("utf-8"),
                payload,
                hashlib.sha512,
            ).hexdigest()
        )
        candidates.append(
            hmac.new(secret.encode("utf-8"), payload, hashlib.sha512).hexdigest()
        )
        return any(hmac.compare_digest(item, signature) for item in candidates)
