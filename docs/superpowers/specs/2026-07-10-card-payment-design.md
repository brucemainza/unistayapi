# Card Payment Design

## Goal
Add Lenco card collection support to the UniStay backend so students can pay for bookings with debit/credit cards, alongside the existing mobile-money flow.

## Constraints
- Live card collections are currently blocked by Lenco for the supplied API key (`errorCode 13`: API key does not have permission to initiate direct card collections). The implementation must be structurally correct and testable via mocks so it works immediately once Lenco enables the permission.
- Card data is PCI DSS sensitive; the backend will encrypt it before sending it to Lenco and will not store raw card numbers.
- Must not break existing mobile-money payments or tests.

## Architecture

### Data model
Add a `payment_type` column to `payments` to distinguish `mobile-money` from `card`. Make `operator` and `phone` nullable because they are only relevant to mobile money. Card-specific metadata (last4, brand, 3DS redirect URL) is stored in the existing `payload` JSON column.

### New API endpoint
`POST /api/payments/lenco/card`
Request body includes:
- `amount`, `currency`, `bookingId`
- `email`
- `customer`: `{ firstName, lastName }`
- `billing`: `{ streetAddress, city, state?, postalCode, country }`
- `card`: `{ number, expiryMonth, expiryYear, cvv }`
- `redirectUrl` (optional)

Response is the standard payment envelope with `status`, `reference`, `lencoReference`, and `meta.authorization.redirect` when 3DS is required.

### Lenco client changes
- `get_encryption_key()`: fetches the RSA public JWK from `GET /access/v2/encryption-key`.
- `encrypt_card_payload(payload)`: builds a standard JWE compact token using `RSA-OAEP-256` + `A256GCM`.
- `charge_card(...)`: sends the encrypted payload to `POST /access/v2/collections/card`.

### Encryption
Use the `jwcrypto` library for JWE. It handles JWK import, RSA-OAEP-256 key encryption, and AES-256-GCM content encryption correctly. This avoids hand-rolling a crypto protocol.

### Service changes
- `PaymentService.initiate_card_payment(request)` creates a payment record, fetches the encryption key, encrypts the card payload, calls Lenco, and updates the record with the response.
- Reuse existing `get_payment_status` and `process_webhook` logic. Map Lenco statuses (`pending`, `successful`, `failed`, `3ds-auth-required`) to the local payment record.

### Tests
- Mock the encryption key and card collection response in `tests/test_payments.py`.
- Verify a successful card initiation returns `3ds-auth-required` with a redirect URL.
- Verify webhook updates a card payment to `successful`.
- Ensure all existing tests still pass.

## Risks and mitigations
- **Wrong encryption format**: JWE RSA-OAEP-256 + A256GCM is the industry standard and matches the JWK returned by Lenco. If Lenco uses a different format, only the `encrypt_card_payload` method needs to change.
- **Live testing blocked**: The feature is fully mock-tested. Live verification can be done as soon as Lenco enables card permissions.
- **PCI scope**: Raw card numbers never hit the database; they are only in memory during request handling and are encrypted before leaving the server.
