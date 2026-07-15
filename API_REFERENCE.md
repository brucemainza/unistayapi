# UniStay API Reference

Generated from the running OpenAPI schema (`/openapi.json`) combined with captured responses. This document is the single source of truth for Flutter mobile integration. Production requests require real integrations; `LENCO_MOCK=false` is mandatory outside isolated tests.

---

## 1. Overview & Conventions

### Base URLs

| Environment                   | URL                                                  |
|-------------------------------|------------------------------------------------------|
| Local development              | `http://localhost:8000`                              |
| Render production (Render Free)| `https://unistay-api.onrender.com`                   |
| Render production (paid plan)  | Same as above, no cold-start delay                    |

**Render Free tier caveat:** The service sleeps after ~15 minutes of inactivity. The first request after idle takes 30-60 seconds to wake up (cold start). The mobile app should show a loading state and retry once if the first request times out.

### Global Response Envelope

Every endpoint — success or error — wraps its payload in:

```json
{
  "status": true,   // false on errors
  "message": "...",
  "data": { ... }   // object, array, or null depending on the endpoint
}
```

The exceptions are `GET /openapi.json` (FastAPI schema, unenveloped) and `GET /api/houses/{id}/static-map` (raw image bytes).

### Authentication

- Obtain a token from `POST /api/auth/register` + `POST /api/auth/verify-otp` **or** `POST /api/auth/signup` + `POST /api/auth/verify-email`.
- Send the token on protected endpoints: `Authorization: Bearer <token>`.
- Token expires after `JWT_EXPIRES_IN` seconds (default **86 400 = 24 hours**).
- **No refresh-token flow.** The mobile app must store the JWT and re-login when it expires.
- In non-production environments, the literal token `dev-student-token` is accepted (convenience for testing).
- In production, all tokens are standard JWTs signed with `JWT_SECRET`.

### Authentication Endpoints Summary

| Endpoint              | OTP Type  | OTP Length | Storage      | Use Case           |
|-----------------------|-----------|------------|--------------|--------------------|
| `/auth/register`      | Account email | 5 digits | DB (`otps` table, HMAC-hashed) | Registration + verified email delivery |
| `/auth/verify-otp`    | Account email | 5 digits | — | Account verification (five-attempt cap) |
| `/auth/resend-otp`    | Account email | 5 digits | — | New code through Resend |
| `/auth/signup`        | Email     | 6 digits   | Redis (hashed) | Email-signup + anti-bot rate limit (5/IP/60s) |
| `/auth/verify-email`  | Email     | 6 digits   | —            | Email verification (5 attempts, then must request new code) |
| `/auth/resend-email-otp` | Email | 6 digits   | —            | New email code (60s cooldown) |

### Field Naming Convention — Important for Flutter

| Domain                                                 | Request keys  | Response keys |
|--------------------------------------------------------|---------------|---------------|
| Auth, Users                                            | `snake_case`  | `snake_case`  |
| Houses, Rooms, Favorites, Universities, Landlords       | `snake_case`  | **camelCase** |
| Payments, Notifications, Bookings, Places              | `snake_case`  | **camelCase** |

Example response keys you will receive:
- Houses: `universityId`, `walkTime`, `driveDistance`, `availableSpaces`, `imageUrls`, `paymentMethods`, `nearbyUniversities`
- Rooms: `houseId`
- Bookings: `studentId`, `houseId`, `roomId`, `moveInDate`, `houseName`, `roomType`, `createdAt`, `updatedAt`
- Notifications: `isRead`, `createdAt`
- Payment details: `bankName`, `accountName`, `accountNumber`, `mobileMoneyProvider`, `mobileMoneyNumber`, `isDefault`

**Dart/Flutter recommendation:** Use `@JsonKey` annotations or a two-branch `fromJson`/`toJson` strategy. Do not assume snake_case across all endpoints.

### Date/Time Format

- All timestamps are **timezone-aware ISO 8601** strings with the `+00:00` offset on production (Postgres).  
  Example: `2026-07-11T09:03:27.853387+00:00`.
- Date-only fields (e.g. `moveInDate`) are plain `YYYY-MM-DD` strings: `2026-08-01`.
- **Note:** Timestamps captured against SQLite memory databases in local tests may omit the offset — this is a test artifact, not a production behavior. Parse with `DateTime.tryParse` using `utc: true`.

### Standard Headers

- `Content-Type: application/json` for JSON request bodies.
- `Authorization: Bearer <token>` for protected endpoints.
- `x-request-id` is returned in every response header. Log it for debugging.

---

## 2. Endpoint Inventory (full)

| Status   | Endpoint                                    | Auth Required          |
|----------|---------------------------------------------|------------------------|
| ✅       | `GET /api/health`                           | None                   |
| ✅       | `POST /api/auth/register`                   | None                   |
| ✅       | `POST /api/auth/login`                      | None                   |
| ✅       | `GET /api/auth/me`                          | Bearer                 |
| ✅       | `POST /api/auth/verify-otp`                | None                   |
| ✅       | `POST /api/auth/resend-otp`                | None                   |
| ✅       | `POST /api/auth/signup`                     | None *(IP rate-limit)* |
| ✅       | `POST /api/auth/verify-email`              | None                   |
| ✅       | `POST /api/auth/resend-email-otp`          | None *(60s cooldown)*  |
| ✅       | `GET /api/users/me`                         | Bearer                 |
| ✅       | `PATCH /api/users/me`                       | Bearer                 |
| ✅       | `GET /api/users/me/stats`                   | Bearer                 |
| ✅       | `GET /api/universities`                     | None                   |
| ✅       | `GET /api/houses`                           | None                   |
| ✅       | `GET /api/houses/{id}`                      | None                   |
| ✅       | `GET /api/houses/{id}/rooms`                | None                   |
| ✅       | `GET /api/houses/{id}/similar`              | None                   |
| ✅       | `GET /api/houses/{id}/eta`                  | None *(Google Maps)*   |
| ✅       | `GET /api/houses/{id}/static-map`           | None *(Google Maps)*   |
| ✅       | `GET /api/houses/nearby`                    | None *(PostGIS)*        |
| ✅       | `POST /api/images/upload`                   | Bearer *(Cloudinary)*  |
| ✅       | `POST /api/images/upload-multiple`          | Bearer *(Cloudinary)*  |
| ✅       | `GET /api/places/autocomplete`              | None *(Google Maps)*   |
| ✅       | `GET /api/places/details`                   | None *(Google Maps)*   |
| ✅       | `GET /api/favorites`                        | Bearer                 |
| ✅       | `POST /api/favorites`                       | Bearer                 |
| ✅       | `DELETE /api/favorites/{house_id}`          | Bearer                 |
| ✅       | `POST /api/bookings`                        | Bearer                 |
| ✅       | `GET /api/bookings`                         | Bearer                 |
| ✅       | `GET /api/bookings/{id}/receipt`            | Bearer                 |
| ✅       | `GET /api/bookings/{id}/receipt.pdf`        | Bearer                 |
| ✅       | `POST /api/bookings/{id}/receipt/email`     | Bearer *(Resend)*      |
| ✅       | `PATCH /api/bookings/{id}/status`           | Bearer *(landlord)*     |
| ✅       | `POST /api/payments/lenco/mobile-money`     | Bearer *(Lenco)*       |
| ✅       | `POST /api/payments/lenco/card`             | Bearer *(Lenco)*       |
| ✅       | `GET /api/payments/lenco/{reference}`       | Bearer                 |
| ✅       | `POST /api/webhooks/lenco`                  | None *(signature)*     |
| ✅       | `GET /api/notifications`                    | Bearer                 |
| ✅       | `PATCH /api/notifications/{id}/read`        | Bearer                 |
| ✅       | `PATCH /api/notifications/read-all`         | Bearer                 |
| ✅       | `GET /api/landlords/me/houses`              | Bearer *(landlord)*     |
| ✅       | `POST /api/landlords/houses`                | Bearer *(landlord)*     |
| ✅       | `PATCH /api/landlords/houses/{id}`          | Bearer *(landlord)*     |
| ✅       | `DELETE /api/landlords/houses/{id}`         | Bearer *(landlord)*     |
| ✅       | `POST /api/landlords/houses/{id}/rooms`     | Bearer *(landlord)*     |
| ✅       | `PATCH /api/landlords/houses/{id}/rooms/{room_id}` | Bearer *(landlord)* |
| ✅       | `DELETE /api/landlords/houses/{id}/rooms/{room_id}` | Bearer *(landlord)* |
| ✅       | `PATCH /api/landlords/houses/{id}/amenities`| Bearer *(landlord)*     |
| ✅       | `PUT /api/landlords/payment-details`         | Bearer *(landlord)*     |
| ✅       | `GET /api/landlords/payment-details`         | Bearer *(landlord)*     |
| ✅       | `GET /api/landlords/bookings`                | Bearer *(landlord)*     |

---

## 3. Endpoints — Reference

### 3.1 Health

#### `GET /api/health`

- **Auth:** none.
- **200**

```json
{
  "status": true,
  "message": "OK",
  "data": {
    "environment": "production",
    "lenco_mock": true,
    "google_maps": {
      "routes": true,
      "places": true
    }
  }
}
```

`google_maps` reflects the startup probe. If Google Maps is unreachable or the key is missing, the app still boots and the flags are `false`. The mobile app does not need to check this — geo endpoints simply return errors.

---

### 3.2 Authentication

#### `POST /api/auth/register`

Register a new account, return a JWT, and send a 5-digit verification code to the registered email through Resend. Returns 502 if Resend does not accept delivery.

- **Auth:** none.
- **Request:** (full_name, phone, email, password, role = `"student"` or `"landlord"`)

```json
{
  "full_name": "John Doe",
  "phone": "0977000001",
  "email": "john@example.com",
  "password": "secret123",
  "role": "student"
}
```

- **200**

```json
{
  "status": true,
  "message": "Registration successful",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIs...",
    "user": {
      "id": "fcc88a43-d1e7-49ef-8647-467d110bcac1",
      "full_name": "John Doe",
      "phone": "0977000001",
      "email": "john@example.com",
      "role": "student",
      "is_verified": false,
      "email_verified": false
    }
  }
}
```

- **409** — phone or email already taken:
  ```json
  { "status": false, "message": "Phone or email already registered", "data": null }
  ```

#### `POST /api/auth/login`

- **Auth:** none.
- **Request:** `{ "phone": "0977000001", "password": "secret123" }`
- **200** — same shape as `register` (token + user).
- **401** — invalid credentials:
  ```json
  { "status": false, "message": "Invalid phone or password", "data": null }
  ```

#### `GET /api/auth/me`

- **Auth:** Bearer.
- **200** — same `user` shape as `register` under `data`.
- **401** — missing or invalid token:
  ```json
  { "status": false, "message": "Authentication failed", "data": null }
  ```

#### `POST /api/auth/verify-otp`

Verifies a **5-digit** phone OTP. In non-production environments any 5-digit code is accepted.

- **Auth:** none.
- **Request:** `{ "user_id": "<uuid>", "code": "12345" }`
- **200** — returns token + user (same shape as `register`).
- **422** — code is not 5 digits.

#### `POST /api/auth/resend-otp`

Request a new 5-digit phone OTP.

- **Auth:** none.
- **Request:** `{ "user_id": "<uuid>" }`
- **200**: `{ "status": true, "message": "OTP resent", "data": { "code": "12345", "expires_in": 600 } }`

> **Production note:** The endpoint creates a new OTP record in the database. Actual SMS delivery is not wired up; it must be added separately.

#### `POST /api/auth/signup` — Email OTP signup

Creates an unverified account and triggers a **6-digit email OTP** in a background task. The code is hashed with SHA-256 and stored in Redis with a 10-minute TTL (`OTP_TTL_SECONDS=600`).

- **Auth:** none. **Rate limit:** 5 requests per IP per 60 seconds.
- **Request:** same body as `register`.
- **201:**

```json
{
  "status": true,
  "message": "Verification code sent",
  "data": {
    "id": "<user-uuid>",
    "email": "john@example.com"
  }
}
```

- **429** — IP limit exceeded:
  ```json
  { "status": false, "message": "Too many signup attempts; please try again later", "data": null }
  ```

If `RESEND_API_KEY` is not configured, the email task is silently skipped (server-side warning logged).

#### `POST /api/auth/verify-email`

Verify a **6-digit** email OTP. Max 5 attempts per code before the code is invalidated.

- **Auth:** none.
- **Request:** `{ "email": "john@example.com", "code": "123456" }`
- **200**: returns token + user (same shape as `register`).
- **401** — wrong or expired code:
  ```json
  { "status": false, "message": "Invalid or expired code", "data": null }
  ```
- **429** — too many attempts:
  ```json
  { "status": false, "message": "Too many attempts; please request a new code", "data": null }
  ```

> **Mobile UX:** When the user enters a wrong code, the error message is "Invalid or expired code". After 5 attempts the message becomes "Too many attempts; please request a new code". The mobile app should surface both messages as-is and offer a "Resend code" button. The 60-second cooldown on `/auth/resend-email-otp` means the resend button should show a countdown timer.

#### `POST /api/auth/resend-email-otp`

Request a new email OTP. Subject to a 60-second resend cooldown per email.

- **Auth:** none.
- **Request:** `{ "email": "john@example.com" }`
- **200**: `{ "status": true, "message": "Verification code sent", "data": null }`
  (Message is generic — does not reveal whether email is registered.)
- **429** — cooldown active:
  ```json
  { "status": false, "message": "Please wait before requesting another code", "data": null }
  ```

---

### 3.3 Users

#### `GET /api/users/me`

- **Auth:** Bearer.
- **200** — same `user` shape as `register`.

#### `PATCH /api/users/me`

Update profile fields (any subset: `full_name`, `email`, `phone`).

- **Auth:** Bearer.
- **Request:** `{ "full_name": "Updated Name" }`
- **200** — updated user object in `data`.

#### `GET /api/users/me/stats`

- **Auth:** Bearer.
- **200:**

```json
{
  "status": true,
  "message": "User stats retrieved",
  "data": {
    "bookings": 1,
    "favorites": 0,
    "notifications": 1
  }
}
```

---

### 3.4 Universities

#### `GET /api/universities`

- **Auth:** none.
- **200:**

```json
{
  "status": true,
  "message": "Universities retrieved",
  "data": [
    {
      "id": "508f49eb-...",
      "name": "University of Zambia",
      "initials": "UNZA",
      "latitude": -15.418,
      "longitude": 28.285
    }
  ]
}
```

These are seeded automatically when the database is empty (6 Zambian universities). Lat/lon are derived from the PostGIS `coords` geography column.

---

### 3.5 Houses

#### `GET /api/houses` — Plain listing/search

- **Auth:** none.
- **Query params:** `university` (name or initials match), `q` (free-text), `amenities` (comma-separated), `min_price`, `max_price`, `page` (1-indexed), `limit`.
- **200** — `data` is a **list** (not paginated):

```json
{
  "status": true,
  "message": "Houses retrieved",
  "data": [
    {
      "id": "5645b2c8-...",
      "name": "Kalingalinga Student Lodge",
      "location": "Kalingalinga, Lusaka",
      "formattedAddress": null,
      "university": "University of Zambia",
      "universityId": "738e2a61-...",
      "price": 1800,
      "walkTime": "12 min",
      "driveDistance": "2.1 km",
      "rating": 4.5,
      "availableSpaces": 6,
      "accent": "#FFFF8C00",
      "amenities": ["WiFi", "Water"],
      "imageUrls": ["https://example.com/photo1.jpg"],
      "paymentMethods": ["mobile_money", "cash"],
      "nearbyUniversities": [
        { "name": "University of Zambia", "distance": "2.1 km" }
      ],
      "latitude": -15.393,
      "longitude": 28.336
    }
  ]
}
```

#### `GET /api/houses?university_id=<id>&radius_m=<meters>` — Geospatial search

- **Auth:** none.
- **Query params:** `university_id` (UUID, required), `radius_m` (default 3000 meters), `page`, `limit`, `q`, `amenities`, `min_price`, `max_price`.
- **200** — `data` is a **pagination object**:

```json
{
  "status": true,
  "message": "Houses retrieved",
  "data": {
    "items": [ /* house objects, each with an extra `distanceM` field */ ],
    "total": 12,
    "page": 1,
    "limit": 20,
    "pages": 1
  }
}
```

**Inconsistency alert:** The same `/api/houses` path returns a flat list for plain search but a paginated `{items, total, page, limit, pages}` wrapper when `university_id` is provided. The mobile app must branch: check `data.items` → if present it's paginated; otherwise it's an array.

Every item in a geospatial response includes a `distanceM` field (meters from the university).

#### `GET /api/houses/{id}`

- **Auth:** none.
- **200** — single house object (same shape as list items).

#### `GET /api/houses/{id}/rooms`

- **Auth:** none.
- **200:**

```json
{
  "status": true,
  "message": "Rooms retrieved",
  "data": [
    {
      "id": "c6367e23-...",
      "houseId": "5645b2c8-...",
      "type": "Shared",
      "rent": 1200,
      "deposit": 600,
      "available": 3,
      "features": ["Bed", "Wardrobe"]
    }
  ]
}
```

#### `GET /api/houses/{id}/similar`

- **Auth:** none.
- **200** — list of house objects.

#### `GET /api/houses/{id}/static-map`

Returns a proxied Google Static Maps image showing the house location. The server key remains on the backend and is never returned to the client. Requires `GOOGLE_MAPS_SERVER_KEY`.

- **Auth:** none.
- **200:** raw `image/png` or the image MIME type returned by Google. This endpoint intentionally does not use the JSON envelope.

#### `GET /api/houses/{id}/eta`

Estimates travel time from a university to the house. Uses Google Routes API with a database+Redis cache.

- **Auth:** none.
- **Query params:** `university_id` (required), `mode` (`DRIVE`, `WALK`, `BICYCLE`, `TRANSIT`; default `DRIVE`).
- **200:**

```json
{
  "status": true,
  "message": "ETA retrieved",
  "data": {
    "durationS": 420,
    "distanceM": 2100,
    "mode": "DRIVE",
    "cached": true
  }
}
```

`cached: true` means the value came from the database or Redis; `false` means a fresh Routes API call was made.

#### `GET /api/houses/nearby`

Returns houses within a radius of a geographic point. Uses PostGIS (production).

- **Auth:** none.
- **Query params:** `latitude`, `longitude`, `radius_km` (default 10).
- **200** — list of house objects, each with a `distanceM` field.

---

### 3.6 Places (Google Maps proxy)

Both endpoints proxy Google Maps Places API (New). They require `GOOGLE_MAPS_SERVER_KEY` with the Places API enabled.

#### `GET /api/places/autocomplete`

- **Auth:** none.
- **Query params:** `input` (search text, required), `session_token` (any string, required), `region` (defaults to `ZM`).
- **200:**

```json
{
  "status": true,
  "message": "Suggestions retrieved",
  "data": {
    "suggestions": [
      { "text": "Lusaka, Zambia", "place_id": "ChIJSaq8PH3zQBkR..." },
      { "text": "Lusaka International Airport", "place_id": "ChIJx5rfzjeIQBkR..." }
    ]
  }
}
```

#### `GET /api/places/details`

- **Auth:** none.
- **Query params:** `place_id` (required), `session_token` (required).
- **200:**

```json
{
  "status": true,
  "message": "Place details retrieved",
  "data": {
    "place_id": "ChIJSaq8PH3zQBkR...",
    "formatted_address": "Lusaka, Zambia",
    "location": {
      "latitude": -15.4154677,
      "longitude": 28.2773267
    }
  }
}
```

---

### 3.7 Images (Cloudinary)

Both endpoints require all three Cloudinary env vars: `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`. Files are uploaded to the folder specified by `CLOUDINARY_FOLDER` (default `unistay`). URLs are permanent (no expiry).

#### `POST /api/images/upload`

Single file upload.

- **Auth:** Bearer.
- **Request:** `multipart/form-data`, field `file` (allowed: `image/jpeg`, `image/png`, `image/webp`, `image/jpg`; max 5 MB).
- **200:** `{ "status": true, "message": "Image uploaded", "data": { "url": "https://res.cloudinary.com/..." } }`
- **422** — invalid type: `{ "status": false, "message": "Only JPEG, PNG, and WebP images are allowed", "data": null }`

#### `POST /api/images/upload-multiple`

- **Auth:** Bearer.
- **Request:** `multipart/form-data`, field `files` (multiple parts with same field name).
- **200:** `{ "status": true, "message": "Images uploaded", "data": { "urls": ["https://...", "https://..."] } }`

---

### 3.8 Favorites

#### `GET /api/favorites`

- **Auth:** Bearer.
- **200** — `data` is a list of house objects.

#### `POST /api/favorites`

- **Auth:** Bearer.
- **Request:** `{ "house_id": "<uuid>" }`
- **200** — returns the favorited house object.

#### `DELETE /api/favorites/{house_id}`

- **Auth:** Bearer.
- **200:** `{ "status": true, "message": "Favorite removed", "data": null }`

---

### 3.9 Bookings

#### `POST /api/bookings`

- **Auth:** Bearer.
- **Request:**

```json
{
  "house_id": "<uuid>",
  "room_id": "<uuid>",
  "move_in_date": "2026-08-01",
  "note": "Looking forward to staying"
}
```

- **200:**

```json
{
  "status": true,
  "message": "Booking created",
  "data": {
    "id": "461d63a9-...",
    "studentId": "fcc88a43-...",
    "houseId": "5645b2c8-...",
    "roomId": "faab9aae-...",
    "moveInDate": "2026-08-01",
    "status": "pending",
    "note": "Looking forward to staying",
    "houseName": "Kalingalinga Student Lodge",
    "roomType": "Shared",
    "createdAt": "2026-07-11T09:01:54.970028+00:00",
    "updatedAt": "2026-07-11T09:01:54.970338+00:00"
  }
}
```

#### `GET /api/bookings`

- **Auth:** Bearer.
- **200** — `data` is a list of booking objects (same shape as single booking).

#### `GET /api/bookings/{id}/receipt`

- **Auth:** Bearer.
- **200** — booking-shaped receipt (includes student, room, house, and payment status).

#### `GET /api/bookings/{id}/receipt.pdf`

- **Auth:** Bearer.
- **200** — printable `application/pdf` receipt.

#### `POST /api/bookings/{id}/receipt/email`

- **Auth:** Bearer.
- **200** — sends the printable PDF receipt to the student's registered email address through Resend.
- **422** — no successful payment exists for the booking yet. Receipt emails are only allowed after Lenco reports a successful payment.

This endpoint is available only after a successful payment. Successful Lenco webhook/status reconciliation also sends the receipt automatically once per payment. The PDF is generated from booking + successful payment details and sent directly through Resend; Redis is not used for receipt delivery.

#### `PATCH /api/bookings/{id}/status`

Update booking status. **Caller must be the landlord who owns the booked house.** Students receive 401.

- **Auth:** Bearer (landlord only).
- **Request:** `{ "status": "confirmed" }`
  Allowed values: `pending`, `confirmed`, `rejected`, `cancelled`.
- **200** — updated booking object.
- **401** — caller is not the right landlord:
  ```json
  { "status": false, "message": "Booking access denied", "data": null }
  ```

---

### 3.10 Payments (Lenco)

With `LENCO_MOCK=false`, payment endpoints call the real Lenco API and require `LENCO_API_KEY`. Use sandbox/test Lenco credentials for manual sweeps before using production keys.

#### `POST /api/payments/lenco/mobile-money`

Initiate a mobile-money payment (e.g., MTN, Airtel).

- **Auth:** Bearer.
- **Request:**

```json
{
  "amount": "150.00",
  "currency": "ZMW",
  "phone": "0977000001",
  "operator": "mtn",
  "country": "zm",
  "booking_id": "<uuid>"
}
```

- **200 (example; Lenco fields vary by payment method):**

```json
{
  "status": true,
  "message": "Payment initiated",
  "data": {
    "reference": "UNISTAY-5283f699615344e9b6",
    "status": "pay-offline",
    "amount": "150.00",
    "currency": "ZMW",
    "paymentType": "mobile-money",
    "lencoReference": "lenco-collection-reference"
  }
}
```

#### `POST /api/payments/lenco/card`

Initiate a card payment. The endpoint requires a student bearer token and must use Lenco sandbox/test credentials before production card collection is enabled.

- **Auth:** Bearer.
- **Request:**

```json
{
  "amount": "150.00",
  "currency": "ZMW",
  "email": "test@example.com",
  "customer": { "first_name": "Test", "last_name": "User" },
  "billing": {
    "street_address": "123 Main St",
    "city": "Lusaka",
    "state": "Lusaka",
    "postal_code": "10101",
    "country": "ZM"
  },
  "card": {
    "number": "4111111111111111",
    "expiry_month": "12",
    "expiry_year": "2030",
    "cvv": "123"
  },
  "redirect_url": "https://example.com/callback"
}
```

- **200 (example; Lenco fields vary by payment method):**

```json
{
  "status": true,
  "message": "Card payment initiated",
  "data": {
    "reference": "UNISTAY-CARD-...",
    "status": "3ds-auth-required",
    "amount": "150.00",
    "currency": "ZMW",
    "paymentType": "card",
    "lencoReference": "lenco-card-reference",
    "meta": {
      "authorization": {
        "mode": "redirect",
        "redirect": "https://checkout.lenco.example/3ds"
      }
    }
  }
}
```

> **Production:** The `meta.authorization.redirect` URL is the real Lenco 3DS page. Open it in a WebView and listen for the callback to your `redirect_url`.

#### `GET /api/payments/lenco/{reference}`

Poll the status of a payment initiated via `POST`.

- **Auth:** Bearer.
- **200** — same shape as the `POST` response.

#### `POST /api/webhooks/lenco`

Receives Lenco event callbacks. In production, `X-Lenco-Signature` is mandatory and validated against `LENCO_WEBHOOK_SECRET`; duplicate event IDs are ignored.

- **Auth:** none (external).
- **Request (simulated):**

```json
{
  "event": "collection.successful",
  "data": {
    "reference": "UNISTAY-5283f699615344e9b6",
    "status": "successful"
  }
}
```

- **200:** `{ "status": true, "message": "Received", "data": null }`

---

### 3.11 Notifications

#### `GET /api/notifications`

- **Auth:** Bearer.
- **200:**

```json
{
  "status": true,
  "message": "Notifications retrieved",
  "data": [
    {
      "id": "1c03949e-...",
      "title": "Payment successful",
      "body": "Your accommodation payment was successful.",
      "isRead": false,
      "createdAt": "2026-07-11T09:03:27.853387+00:00"
    }
  ]
}
```

#### `PATCH /api/notifications/{id}/read`

Mark a single notification as read.

- **Auth:** Bearer.
- **200** — updated notification object (same shape, `isRead: true`).

#### `PATCH /api/notifications/read-all`

Mark all notifications for the current user as read.

- **Auth:** Bearer.
- **200:** `{ "status": true, "message": "Notifications marked read", "data": { "updated": 3 } }`

---

### 3.12 Landlords

All landlord endpoints require a user with `role: "landlord"`. Students receive:

```json
{ "status": false, "message": "Landlord access required", "data": null }
```

#### `GET /api/landlords/me/houses`

- **Auth:** Bearer (landlord).
- **200** — `data` is a list of house objects.

#### `POST /api/landlords/houses`

Create a new house with rooms, amenities, and images in a single call.

- **Auth:** Bearer (landlord).
- **Request:** `snake_case` body, response is `camelCase`.

```json
{
  "name": "New House",
  "location": "Lusaka",
  "latitude": -15.3918,
  "longitude": 28.3296,
  "university_id": "<uuid>",
  "price": 2000,
  "walk_time": "10 min",
  "drive_distance": "1.5 km",
  "rating": 4.0,
  "available_spaces": 4,
  "accent": "#FF0000FF",
  "payment_methods": ["mobile_money"],
  "amenities": ["WiFi"],
  "images": [{ "url": "https://example.com/pic.jpg", "order": 0 }],
  "rooms": [{ "type": "Single", "rent": 2000, "deposit": 1000, "available": 2, "features": ["Bed"] }]
}
```

- **200** — created house object (camelCase response keys).

#### `PATCH /api/landlords/houses/{id}`

Partial update. Landlord must own the house.

- **Auth:** Bearer (landlord).
- **Request:** any subset of house fields.
- **200** — updated house.

#### `POST /api/landlords/houses/{id}/rooms`

Add a room to an existing house.

- **Auth:** Bearer (landlord).
- **Request:** `{ "type": "Single", "rent": 2000, "deposit": 1000, "available": 2, "features": ["Bed"] }`
- **200** — created room object.

#### `PATCH /api/landlords/houses/{id}/rooms/{room_id}`

Update a room.

- **Auth:** Bearer (landlord).
- **Request:** `{ "rent": 2600 }` (any subset).
- **200** — updated room.

#### `DELETE /api/landlords/houses/{id}/rooms/{room_id}`

Delete a room.

- **Auth:** Bearer (landlord).
- **200:** `{ "status": true, "message": "Room deleted", "data": null }`

#### `PATCH /api/landlords/houses/{id}/amenities`

Replace the entire amenities list.

- **Auth:** Bearer (landlord).
- **Request:** `{ "amenities": ["WiFi", "Parking"] }`
- **200** — updated house with new amenities.

#### `DELETE /api/landlords/houses/{id}`

**Soft-delete** a house. Sets `deleted_at` to now; the house is hidden from all search/list/detail/public queries. Rooms and bookings remain in the database but are unreachable through public endpoints.

- **Auth:** Bearer (landlord).
- **200:** `{ "status": true, "message": "House deleted", "data": null }`
- **404** — house does not exist or is already deleted:
  ```json
  { "status": false, "message": "House not found", "data": null }
  ```

#### `PUT /api/landlords/payment-details`

Save landlord payment details (bank/mobile-money). Upserts — creates or replaces.

- **Auth:** Bearer (landlord).
- **Request:**

```json
{
  "bank_name": "Zambia National Bank",
  "account_name": "Test Landlord",
  "account_number": "1234567890",
  "mobile_money_provider": "mtn",
  "mobile_money_number": "0977000001",
  "is_default": true
}
```

- **200:** returns the saved object with camelCase keys (`bankName`, `accountName`, etc.).

#### `GET /api/landlords/payment-details`

- **Auth:** Bearer (landlord).
- **200** — same shape as PUT response.

#### `GET /api/landlords/bookings`

- **Auth:** Bearer (landlord).
- **200** — list of booking objects for the landlord's houses.

---

## 4. Mobile Integration Checklist

This section is a one-page checklist for the Flutter developer integrating the API.

### 4.1 Auth Flow — the two paths

**Path A: account email OTP** (5 digits, delivered by Resend)
1. `POST /api/auth/register` → receives token + unverified user. Token works immediately.
2. (Optional) `POST /api/auth/verify-otp` → marks user verified.
3. Store the JWT. No expiry endpoint — trade-off is 24h or re-login.

**Path B: Email OTP** (secure, Redis-backed in prod)
1. `POST /api/auth/signup` → receives `{id, email}`. A 6-digit code was emailed.
   - Rate limit: 5/IP/60s. On 429, show a cooldown UI.
2. User enters 6-digit code → `POST /api/auth/verify-email` → receives token + verified user.
   - Wrong code → 401 "Invalid or expired code". Max 5 attempts → 429 "Too many attempts".
   - Resend: `POST /api/auth/resend-email-otp` → 60s cooldown. Show countdown.

**Token lifecycle:**
- 24-hour expiry (configurable via `JWT_EXPIRES_IN`).
- **No refresh token.** When the API returns 401, redirect user to login.
- App must retry at least once before showing login (network flake, cold start).

### 4.2 Response Envelope

Every endpoint (except `/openapi.json`) returns:
```dart
class ApiResponse<T> {
  bool status;
  String message;
  T? data; // nullable! data can be null on errors or specific endpoints
}
```

**`data` can be:**
- `List<dynamic>` — `GET /api/houses`, `GET /api/favorites`, etc.
- `Map<String, dynamic>` — pagination wrappers, single objects.
- `null` — DELETE operations, `resend-email-otp`, error responses.
- `int` — `read-all` returns `{"updated": 3}` under data.

**✅ Do:** deserialize `data` as `dynamic`, then cast based on the endpoint.
**❌ Don't:** assume `data` is always a `Map`.

### 4.3 Casing — you must branch

```dart
// Auth / Users → snake_case response
// Example: register/login returns user.full_name

// Houses, Rooms, Payments, Bookings, Notifications, Landlords, Favorites → camelCase response
// Example: house.hasField('universityId') is true, house.hasField('university_id') is false
```

**Request bodies** are always `snake_case` regardless of domain.

**Recommended Dart approach:**
- Create a `JsonKey(name: 'full_name')` mapping for auth/user models.
- Create a `JsonKey(name: 'universityId')` mapping for housing/booking/payment models.
- Or use a single `fromJson` with a `renameKeys` helper that converts `camelCase` ↔ `snake_case` when reading.

### 4.4 Nullables / Optionals

Always nullable in Dart models (`?`):

| Field              | Why                                          |
|-------------------|-----------------------------------------------|
| `formattedAddress`| Populated after async reverse-geocode (may be null at first load) |
| `universityId`    | Houses not tied to a university               |
| `note` (booking)  | Optional booking note                          |
| `houseName`, `roomType` (booking) | Present in booking responses but not in create body |

### 4.5 Error Messages — display as-is

The `message` field in error envelopes is user-facing text. ✅ Pass it to your UI directly (no custom mapping needed):

| Status | `message` snippet                            |
|--------|----------------------------------------------|
| 401    | `Authentication failed`, `Invalid or expired code` |
| 409    | `Phone or email already registered`           |
| 429    | `Too many signup attempts`, `Please wait before requesting another code` |
| 404    | `House not found`, `Favorite not found`       |
| 422    | `body.phone: value_error...` (validation)      |

### 4.6 Rate Limits — handle gracefully

| Endpoint                | Limit                     | Behavior on 429              |
|-------------------------|---------------------------|------------------------------|
| `/auth/signup`          | 5 / IP / 60s              | Show "Too many attempts"     |
| `/auth/resend-email-otp`| 1 / email / 60s           | Show countdown (60s)         |
| `/auth/verify-email`    | 5 attempts / code         | Offer "Resend code" button   |

When you receive a 429, extract the `message` and show it. Do not retry aggressively — wait at least 5s.

### 4.7 External-Dependency Endpoints

These endpoints depend on environment variables and may return errors if the service is not configured. The mobile app should handle failure gracefully (show a retry UI, not a crash):

| Endpoint                            | Dependency       |
|-------------------------------------|------------------|
| `GET /api/houses/{id}/eta`          | Google Maps Routes API |
| `GET /api/houses/{id}/static-map`   | Google Maps Static Maps API |
| `GET /api/places/*`                 | Google Maps Places API (New) |
| `POST /api/images/*`                | Cloudinary       |
| `POST /api/payments/lenco/*`        | Lenco collections API |

### 4.8 Render Cold Start (Free tier)

On Render Free tier the API container sleeps after ~15 minutes idle. The first request wakes it:

- **Timeout:** 30-60 seconds.
- **App behavior:** Show a "Connecting..." loading state. Set an HTTP timeout of 60s. If the first request fails/timeouts, retry once after 3s.
- **Paid plans:** No cold start; standard response times.

### 4.9 Checklist Summary

- [ ] Envelope parser (`status`, `message`, `data: dynamic`).
- [ ] two-branch casing layer (Auth/Users → snake_case; everything else → camelCase).
- [ ] Auth flow tested end-to-end (signup → verify-email → token → `/auth/me`).
- [ ] All nullable fields modeled as `?`.
- [ ] `diff` checked: `GET /api/houses` returns list; `GET /api/houses?university_id=X` returns `{items, total}`.
- [ ] 429 handling with user-visible cooldown messages.
- [ ] Google Maps / Cloudinary endpoints have graceful-fallback UI.
- [ ] Bearer token expiry handling (401 → redirect to login).
- [ ] Cold-start timeout (60s connect + 3s retry).
- [ ] `x-request-id` logged in crash reports.

---

## 5. Render Deployment Notes

Deploying on Render requires:

| Service            | Notes                                              |
|--------------------|----------------------------------------------------|
| **Postgres**       | Use **Supabase** (bundles PostGIS 3.4+). Set `DATABASE_URL` to the Supabase session-pooler URI (`postgresql+asyncpg://...:6543/postgres`). |
| **Redis**          | Use **Upstash** free tier. Set `REDIS_URL` = `rediss://...:6379`. |
| **Google Maps**    | `GOOGLE_MAPS_SERVER_KEY` with Routes API and Places API (New) enabled + linked billing account. |
| **Cloudinary**     | All three `CLOUDINARY_*` env vars. |
| **Lenco**          | Set `LENCO_MOCK=false`, `LENCO_API_KEY`, and `LENCO_WEBHOOK_SECRET`; prefer sandbox/test keys for verification. |
| **Resend (email)** | `RESEND_API_KEY` and `RESEND_FROM_EMAIL`; production startup fails if missing. |

The Docker image runs `alembic upgrade head` at startup, which self-enables PostGIS via `CREATE EXTENSION IF NOT EXISTS postgis` in the initial migration.

---

## 6. Internal-Only Endpoints (Do Not Integrate)

- `GET /openapi.json` — OpenAPI schema (unenveloped JSON).
- `GET /docs` and `/redoc` — auto-generated FastAPI documentation UI.
