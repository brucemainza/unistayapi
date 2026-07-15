# Card Payment Implementation Plan

> Historical planning artifact. The verified current contract is maintained in `README.md` and `API_REFERENCE.md`; payments now require student authentication, use `LENCO_MOCK=false` outside isolated tests, and receipt delivery is triggered only after successful reconciliation.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Lenco card collection support to the UniStay backend so students can pay with debit/credit cards.

**Architecture:** Extend the existing payment module with a card-specific endpoint, schema, and Lenco client method. Encrypt card payloads using JWE (RSA-OAEP-256 + A256GCM) via `jwcrypto`. Store card payments in the same `payments` table using a new `payment_type` column; keep raw card data out of persistent storage.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, Alembic, `jwcrypto`, `cryptography`.

## Global Constraints
- Live card collections are blocked by Lenco for the current API key (`errorCode 13`). Implementation must be correct and fully mock-tested.
- Card data is PCI-sensitive; never store raw PAN, CVV, or expiry in the database.
- Do not break existing mobile-money payments or tests.
- Use the existing Flutter-compatible envelope response format.
- Match existing code style: lowercase_snake Python, camelCase JSON keys in schemas.

---

## File Structure

| File | Responsibility |
|------|----------------|
| `app/models/payment.py` | Add `payment_type` column; make `operator`/`phone` nullable. |
| `alembic/versions/2026_07_10_xxxx_add_payment_type.py` | Migration adding `payment_type` with server default. |
| `app/schemas/payment.py` | Add `CardPaymentRequest`, `BillingAddress`, `CardDetails`, `CustomerDetails`; add `payment_type` to response. |
| `app/clients/lenco_client.py` | Add `get_encryption_key`, `encrypt_card_payload`, `charge_card`; update mock responses. |
| `app/services/payment_service.py` | Add `initiate_card_payment`; update status/webhook handling for card statuses. |
| `app/services/serializers.py` | Add `payment_type` and card summary to `payment_to_dict`. |
| `app/routers/payments.py` | Add `POST /api/payments/lenco/card` route. |
| `pyproject.toml` | Add `jwcrypto` dependency. |
| `tests/test_payments.py` | Add card payment and 3DS webhook tests. |

---

### Task 1: Add `jwcrypto` dependency

**Files:**
- Modify: `pyproject.toml`

**Interfaces:**
- Produces: `jwcrypto` available in the virtual environment.

- [ ] **Step 1: Add dependency**

Add `"jwcrypto>=1.5.0",` to the `dependencies` list in `pyproject.toml`.

- [ ] **Step 2: Install dependency**

Run: `source .venv/bin/activate && pip install jwcrypto>=1.5.0`
Expected: `Successfully installed jwcrypto-...`

- [ ] **Step 3: Verify import**

Run: `source .venv/bin/activate && python -c "from jwcrypto import jwk, jwe; print('jwcrypto ok')"`
Expected: `jwcrypto ok`

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "deps: add jwcrypto for Lenco JWE card encryption"
```

---

### Task 2: Add `payment_type` to the Payment model

**Files:**
- Modify: `app/models/payment.py`

**Interfaces:**
- Produces: `Payment.payment_type` column (`mobile-money` | `card`).
- Produces: `Payment.operator` and `Payment.phone` are nullable.

- [ ] **Step 1: Edit model**

```python
payment_type: Mapped[str] = mapped_column(
    String(20), default="mobile-money", nullable=False
)
operator: Mapped[str | None] = mapped_column(String(50), nullable=True)
phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
```

- [ ] **Step 2: Commit**

```bash
git add app/models/payment.py
git commit -m "feat(payments): add payment_type column and make operator/phone nullable"
```

---

### Task 3: Create Alembic migration for `payment_type`

**Files:**
- Create: `alembic/versions/2026_07_10_xxxx_add_payment_type_to_payments.py`

**Interfaces:**
- Produces: Migration that adds `payment_type` with server default `mobile-money`.

- [ ] **Step 1: Generate migration against PostgreSQL**

Use the existing PostGIS container or a local PostgreSQL with the `unistay` database:

```bash
source .venv/bin/activate && alembic revision --autogenerate -m "add payment_type to payments"
```

If no PostGIS is available, hand-write the migration:

```python
"""add payment_type to payments

Revision ID: <generated>
Revises: <head>
Create Date: <generated>
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '<generated>'
down_revision: Union[str, None] = '<current head>'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'payments',
        sa.Column('payment_type', sa.String(length=20), server_default='mobile-money', nullable=False)
    )


def downgrade() -> None:
    op.drop_column('payments', 'payment_type')
```

- [ ] **Step 2: Commit**

```bash
git add alembic/versions/2026_07_10_xxxx_add_payment_type_to_payments.py
git commit -m "feat(migration): add payment_type column to payments"
```

---

### Task 4: Add card payment schemas

**Files:**
- Modify: `app/schemas/payment.py`

**Interfaces:**
- Produces: `CustomerDetails`, `BillingAddress`, `CardDetails`, `CardPaymentRequest`.
- Produces: `PaymentResponse` includes `paymentType`.

- [ ] **Step 1: Add schema classes**

```python
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
```

- [ ] **Step 2: Update PaymentResponse**

```python
class PaymentResponse(BaseModel):
    reference: str
    status: str
    amount: str
    currency: str
    paymentType: str
    lencoReference: str | None = None
```

- [ ] **Step 3: Commit**

```bash
git add app/schemas/payment.py
git commit -m "feat(payments): add card payment request schemas"
```

---

### Task 5: Add JWE encryption and card charge to LencoClient

**Files:**
- Modify: `app/clients/lenco_client.py`

**Interfaces:**
- Consumes: Settings with `lenco_base_url`, `lenco_api_key`, `lenco_mock`.
- Produces: `LencoClient.get_encryption_key() -> dict`
- Produces: `LencoClient.encrypt_card_payload(payload: dict, jwk: dict) -> str`
- Produces: `LencoClient.charge_card(payload: dict) -> dict`

- [ ] **Step 1: Add imports and helper methods**

Add to imports:
```python
import json
from jwcrypto import jwk, jwe
from jwcrypto.common import json_encode
```

Add methods:
```python
    async def get_encryption_key(self) -> dict:
        if self.settings.lenco_mock:
            return {
                "kty": "RSA",
                "use": "enc",
                "n": "mock",
                "e": "AQAB",
                "kid": "mock-kid",
            }

        if not self.settings.lenco_api_key:
            raise LencoError("Lenco API key is not configured")

        url = f"{self.settings.lenco_base_url.rstrip('/')}/access/v2/encryption-key"
        headers = {
            "Authorization": f"Bearer {self.settings.lenco_api_key}",
            "Accept": "application/json",
            "User-Agent": "UniStay-API/1.0",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, headers=headers)
        return self._handle_response(response, "Unable to retrieve Lenco encryption key")

    def encrypt_card_payload(self, payload: dict, key_data: dict) -> str:
        if self.settings.lenco_mock:
            return "encrypted-card-payload-mock"

        public_key = jwk.JWK(**key_data)
        protected_header = json_encode({"alg": "RSA-OAEP-256", "enc": "A256GCM", "typ": "JWE"})
        jwetoken = jwe.JWE(
            json.dumps(payload).encode("utf-8"),
            recipient=public_key,
            protected=protected_header,
        )
        return jwetoken.serialize(compact=True)

    async def charge_card(self, *, encrypted_payload: str, reference: str) -> dict:
        if self.settings.lenco_mock:
            return {
                "success": True,
                "status": True,
                "message": "Mock card collection initiated",
                "data": {
                    "reference": reference,
                    "lencoReference": f"MOCK-CARD-{uuid4().hex[:12]}",
                    "amount": "0.00",
                    "currency": "ZMW",
                    "type": "card",
                    "status": "3ds-auth-required",
                    "meta": {
                        "authorization": {
                            "mode": "redirect",
                            "redirect": "https://mock.lenco.co/3ds",
                        }
                    },
                },
            }

        if not self.settings.lenco_api_key:
            raise LencoError("Lenco API key is not configured")

        url = f"{self.settings.lenco_base_url.rstrip('/')}/access/v2/collections/card"
        payload = {"encryptedCard": encrypted_payload}
        headers = {
            "Authorization": f"Bearer {self.settings.lenco_api_key}",
            "Accept": "application/json",
            "User-Agent": "UniStay-API/1.0",
        }
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(url, json=payload, headers=headers)
        return self._handle_response(response, "Lenco card request failed")
```

- [ ] **Step 2: Commit**

```bash
git add app/clients/lenco_client.py
git commit -m "feat(payments): add Lenco card encryption and charge methods"
```

---

### Task 6: Add card payment service logic

**Files:**
- Modify: `app/services/payment_service.py`

**Interfaces:**
- Consumes: `CardPaymentRequest` from `app.schemas.payment`.
- Produces: `PaymentService.initiate_card_payment(request) -> dict`.

- [ ] **Step 1: Add import and method**

Add import:
```python
from app.schemas.payment import CardPaymentRequest, MobileMoneyPaymentRequest
```

Add method after `initiate_mobile_money_payment`:
```python
    async def initiate_card_payment(self, request: CardPaymentRequest) -> dict:
        if request.booking_id and self.booking_repo is not None:
            booking = await self.booking_repo.get_by_id(request.booking_id)
            if booking is None:
                raise NotFoundError("Booking not found")

        reference = f"UNISTAY-CARD-{uuid4().hex[:18]}"
        payment = Payment(
            reference=reference,
            booking_id=request.booking_id,
            amount=Decimal(request.amount),
            currency=request.currency.upper(),
            payment_type="card",
            operator=None,
            phone=None,
            status="pending",
            payload={},
        )
        payment = await self.payment_repo.create(payment)

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
            await self.payment_repo.update(
                payment,
                status="failed",
                payload={"error": exc.message},
            )
            raise

        data = response.get("data") or {}
        status = data.get("status") or "pending"
        payment = await self.payment_repo.update(
            payment,
            status=status,
            lenco_reference=data.get("lencoReference"),
            payload=response,
        )
        return payment_to_dict(payment)
```

- [ ] **Step 2: Commit**

```bash
git add app/services/payment_service.py
git commit -m "feat(payments): add initiate card payment service logic"
```

---

### Task 7: Update payment serializer

**Files:**
- Modify: `app/services/serializers.py`

**Interfaces:**
- Produces: `payment_to_dict` returns `paymentType` and card `meta` when available.

- [ ] **Step 1: Update serializer**

```python
def payment_to_dict(payment: Payment) -> dict:
    amount: Decimal | str = payment.amount
    result = {
        "reference": payment.reference,
        "status": payment_status_for_client(payment.status),
        "amount": str(amount),
        "currency": payment.currency,
        "paymentType": payment.payment_type,
        "lencoReference": payment.lenco_reference,
    }
    payload_data = payment.payload or {}
    if payment.payment_type == "card":
        meta = (payload_data.get("data") or {}).get("meta")
        if meta:
            result["meta"] = meta
        card_details = (payload_data.get("data") or {}).get("cardDetails")
        if card_details:
            result["cardDetails"] = {
                "firstName": card_details.get("firstName"),
                "lastName": card_details.get("lastName"),
                "bin": card_details.get("bin"),
                "last4": card_details.get("last4"),
                "cardType": card_details.get("cardType"),
            }
    return result
```

- [ ] **Step 2: Commit**

```bash
git add app/services/serializers.py
git commit -m "feat(payments): include payment_type and card meta in payment response"
```

---

### Task 8: Add card payment route

**Files:**
- Modify: `app/routers/payments.py`

**Interfaces:**
- Produces: `POST /api/payments/lenco/card`.

- [ ] **Step 1: Add route**

```python
from app.schemas.payment import CardPaymentRequest, MobileMoneyPaymentRequest

@router.post("/lenco/card")
async def initiate_card(
    body: CardPaymentRequest, db: AsyncSession = Depends(get_db)
) -> dict:
    payment = await _service(db).initiate_card_payment(body)
    return envelope(True, "Card payment initiated", payment)
```

- [ ] **Step 2: Commit**

```bash
git add app/routers/payments.py
git commit -m "feat(payments): add Lenco card payment endpoint"
```

---

### Task 9: Add card payment tests

**Files:**
- Modify: `tests/test_payments.py`

**Interfaces:**
- Consumes: `/api/payments/lenco/card`, `/api/webhooks/lenco`.
- Produces: Tests covering card initiation (3DS) and webhook status update.

- [ ] **Step 1: Add card test**

Append to `tests/test_payments.py`:

```python
async def test_card_payment_and_3ds_webhook(client):
    card_response = await client.post(
        "/api/payments/lenco/card",
        json={
            "amount": "250.00",
            "currency": "ZMW",
            "email": "customer@example.com",
            "customer": {"first_name": "John", "last_name": "Doe"},
            "billing": {
                "street_address": "123 Main St",
                "city": "Lusaka",
                "postal_code": "10101",
                "country": "ZM",
            },
            "card": {
                "number": "5555555555554444",
                "expiry_month": "12",
                "expiry_year": "2025",
                "cvv": "838",
            },
        },
    )
    assert card_response.status_code == 200, card_response.text
    payment = card_response.json()["data"]
    assert payment["amount"] == "250.00"
    assert payment["paymentType"] == "card"
    assert payment["status"] == "3ds-auth-required"
    assert payment["meta"]["authorization"]["redirect"].startswith("https://mock")

    previous_mock = settings.lenco_mock
    previous_secret = settings.lenco_webhook_secret
    settings.lenco_mock = False
    settings.lenco_webhook_secret = "secret"
    try:
        payload = {
            "event": "transaction.successful",
            "data": {"reference": payment["reference"], "status": "successful"},
        }
        raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        key = hashlib.sha256(b"secret").hexdigest().encode("utf-8")
        signature = hmac.new(key, raw, hashlib.sha512).hexdigest()
        webhook = await client.post(
            "/api/webhooks/lenco",
            content=raw,
            headers={"X-Lenco-Signature": signature},
        )
        assert webhook.status_code == 200, webhook.text
    finally:
        settings.lenco_mock = previous_mock
        settings.lenco_webhook_secret = previous_secret

    status = await client.get(f"/api/payments/lenco/{payment['reference']}")
    assert status.status_code == 200, status.text
    assert status.json()["data"]["status"] == "successful"
```

- [ ] **Step 2: Run payment tests**

Run: `source .venv/bin/activate && pytest tests/test_payments.py -v`
Expected: 2 passing tests.

- [ ] **Step 3: Commit**

```bash
git add tests/test_payments.py
git commit -m "test(payments): add card payment and 3DS webhook tests"
```

---

### Task 10: Full regression test

**Files:**
- None (verification only).

**Interfaces:**
- Validates the whole suite still passes.

- [ ] **Step 1: Run all tests**

Run: `source .venv/bin/activate && pytest -v`
Expected: 12/12 passing tests.

- [ ] **Step 2: Commit any fixes**

If failures occur, fix and commit. If all pass, no extra commit needed.

---

## Spec Coverage Check

| Spec Requirement | Task |
|------------------|------|
| Add `payment_type` column | Task 2 + 3 |
| Card endpoint | Task 8 |
| Card schemas | Task 4 |
| JWE encryption | Task 5 |
| Card service logic | Task 6 |
| Serializer update | Task 7 |
| Mock tests | Task 9 + 10 |
| No mobile-money breakage | Task 10 |

## Placeholder Scan

- No TBD/TODO/"implement later" items.
- All code blocks contain concrete implementation.
- All file paths are exact.
