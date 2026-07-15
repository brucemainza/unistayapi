"""Business logic for Lenco payments and webhooks."""

import hashlib
import hmac
import json
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from app.clients.lenco_client import LencoClient
from app.config import settings
from app.exceptions import AuthError, LencoError, NotFoundError, ValidationError
from app.models.notification import Notification
from app.models.payment import Payment
from app.repositories.booking_repo import BookingRepository
from app.repositories.notification_repo import NotificationRepository
from app.repositories.payment_repo import PaymentRepository
from app.schemas.payment import CardPaymentRequest, MobileMoneyPaymentRequest
from app.services.email import send_booking_receipt_email
from app.services.receipt import build_receipt_payload, receipt_filename, render_receipt_pdf
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
        self,
        request: MobileMoneyPaymentRequest,
        user_id: str | None = None,
    ) -> dict:
        if user_id is None:
            raise AuthError("Authentication required")
        if request.booking_id and self.booking_repo is not None:
            booking = await self.booking_repo.get_by_id(request.booking_id)
            if booking is None:
                raise NotFoundError("Booking not found")
            if user_id is None or booking.student_id != user_id:
                raise AuthError("Booking access denied")

        reference = f"UNISTAY-{uuid4().hex[:18]}"
        payment = Payment(
            reference=reference,
            booking_id=request.booking_id,
            user_id=user_id,
            amount=Decimal(request.amount),
            currency=request.currency.upper(),
            operator=request.operator,
            phone=request.phone,
            status="pending",
            payload={},
        )
        await self.payment_repo.add(payment)
        try:
            response = await self.lenco_client.charge_mobile_money(
                amount=request.amount,
                reference=reference,
                phone=request.phone,
                operator=request.operator,
                country=request.country,
            )
        except LencoError as exc:
            await self.payment_repo.apply(
                payment,
                status="failed",
                payload={"error": exc.message},
            )
            await self.payment_repo.commit_and_refresh(payment)
            raise

        data = response.get("data") or {}
        status = data.get("status") or "processing"
        await self.payment_repo.apply(
            payment,
            status=status,
            lenco_reference=data.get("lencoReference"),
            payload=response,
        )
        await self.payment_repo.commit_and_refresh(payment)
        await self._send_receipt_if_successful(payment)
        return payment_to_dict(payment)

    async def initiate_card_payment(
        self,
        request: CardPaymentRequest,
        user_id: str | None = None,
    ) -> dict:
        if user_id is None:
            raise AuthError("Authentication required")
        if request.booking_id and self.booking_repo is not None:
            booking = await self.booking_repo.get_by_id(request.booking_id)
            if booking is None:
                raise NotFoundError("Booking not found")
            if user_id is None or booking.student_id != user_id:
                raise AuthError("Booking access denied")

        reference = f"UNISTAY-CARD-{uuid4().hex[:18]}"
        payment = Payment(
            reference=reference,
            booking_id=request.booking_id,
            user_id=user_id,
            amount=Decimal(request.amount),
            currency=request.currency.upper(),
            payment_type="card",
            operator=None,
            phone=None,
            status="pending",
            payload={},
        )
        await self.payment_repo.add(payment)

        try:
            key_response = await self.lenco_client.get_encryption_key()
            key_data = key_response.get("data") or key_response

            lenco_payload = {
                "reference": reference,
                "email": request.email,
                "amount": request.amount,
                "currency": request.currency.upper(),
                "customer": {
                    "firstName": request.customer.first_name,
                    "lastName": request.customer.last_name,
                },
                "billing": {
                    "streetAddress": request.billing.street_address,
                    "city": request.billing.city,
                    "state": request.billing.state or "",
                    "postalCode": request.billing.postal_code,
                    "country": request.billing.country.upper(),
                },
                "card": {
                    "number": request.card.number,
                    "expiryMonth": request.card.expiry_month,
                    "expiryYear": request.card.expiry_year,
                    "cvv": request.card.cvv,
                },
            }
            if request.redirect_url:
                lenco_payload["redirectUrl"] = request.redirect_url

            encrypted = self.lenco_client.encrypt_card_payload(lenco_payload, key_data)
            response = await self.lenco_client.charge_card(
                encrypted_payload=encrypted, reference=reference
            )
        except LencoError as exc:
            await self.payment_repo.apply(
                payment,
                status="failed",
                payload={"error": exc.message},
            )
            await self.payment_repo.commit_and_refresh(payment)
            raise

        data = response.get("data") or {}
        status = data.get("status") or "pending"
        await self.payment_repo.apply(
            payment,
            status=status,
            lenco_reference=data.get("lencoReference"),
            payload=response,
        )
        await self.payment_repo.commit_and_refresh(payment)
        await self._send_receipt_if_successful(payment)
        return payment_to_dict(payment)

    async def get_payment_status(
        self, reference: str, user_id: str | None = None
    ) -> dict:
        if user_id is None:
            raise AuthError("Authentication required")
        payment = await self.payment_repo.get_by_reference(reference)
        if payment is None:
            raise NotFoundError("Payment not found")
        if payment.user_id is not None:
            if user_id is None or payment.user_id != user_id:
                raise AuthError("Payment access denied")

        if not settings.lenco_mock and payment.status in {"pending", "processing", "pay-offline"}:
            response = await self.lenco_client.get_collection_status(reference)
            data = response.get("data") or {}
            status = data.get("status")
            if status:
                await self.payment_repo.apply(
                    payment,
                    status=status,
                    lenco_reference=data.get("lencoReference") or payment.lenco_reference,
                    payload=response,
                )
                await self.payment_repo.commit_and_refresh(payment)
                await self._send_receipt_if_successful(payment)
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

        # Idempotency: deduplicate by event id. Lenco events include an
        # `event_id` (or fall back to a hash of the payload when absent). If we
        # have already processed this exact event, do nothing.
        event_id = (
            data.get("eventId")
            or data.get("id")
            or event.get("eventId")
            or event.get("id")
            or hashlib.sha256(payload).hexdigest()
        )
        if payment.last_event_id is not None and payment.last_event_id == event_id:
            return

        event_name = event.get("event", "")
        status = data.get("status")
        if event_name.endswith(".successful") or status == "successful":
            status = "successful"
        elif event_name.endswith(".failed") or status == "failed":
            status = "failed"

        if status not in LENCO_TO_CLIENT_STATUS:
            return

        normalised_status = LENCO_TO_CLIENT_STATUS[status]
        previous_status = payment.status
        status_transitioned = previous_status != normalised_status

        await self.payment_repo.apply(
            payment,
            status=normalised_status,
            lenco_reference=data.get("lencoReference") or payment.lenco_reference,
            last_event_id=event_id,
            payload=event,
        )
        await self.payment_repo.commit_and_refresh(payment)
        await self._send_receipt_if_successful(payment)

        # Only create a notification when the status actually transitions, so
        # redelivered webhook events do not spam the user.
        if (
            status_transitioned
            and status == "successful"
            and self.notification_repo is not None
            and payment.booking is not None
        ):
            await self.notification_repo.add(
                Notification(
                    user_id=payment.booking.student_id,
                    title="Payment successful",
                    body="Your accommodation payment was successful.",
                )
            )
            await self.notification_repo.commit()

    async def _send_receipt_if_successful(self, payment: Payment) -> None:
        if payment.status not in {"successful", "completed"}:
            return
        if payment.receipt_sent_at is not None:
            return
        if payment.booking is None and payment.booking_id is not None:
            reloaded = await self.payment_repo.get_by_reference(payment.reference)
            if reloaded is not None:
                payment = reloaded
        if payment.booking is None:
            return

        receipt = build_receipt_payload(payment.booking, payment)
        filename = receipt_filename(payment.booking.id)
        pdf_bytes = render_receipt_pdf(receipt)
        sent = await send_booking_receipt_email(
            payment.booking.student.email,
            pdf_bytes=pdf_bytes,
            filename=filename,
        )
        if not sent:
            return

        await self.payment_repo.apply(
            payment, receipt_sent_at=datetime.now(timezone.utc)
        )
        await self.payment_repo.commit_and_refresh(payment)

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
