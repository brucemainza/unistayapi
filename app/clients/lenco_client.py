"""Async client for the Lenco collections API."""

import json
from uuid import uuid4

import httpx
from jwcrypto import jwe, jwk
from jwcrypto.common import json_encode

from app.config import Settings
from app.exceptions import LencoError


class LencoClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def charge_mobile_money(
        self,
        *,
        amount: str,
        reference: str,
        phone: str,
        operator: str,
        country: str = "zm",
    ) -> dict:
        if self.settings.lenco_mock:
            return {
                "success": True,
                "status": True,
                "message": "Mock collection initiated",
                "data": {
                    "reference": reference,
                    "lencoReference": f"MOCK-{uuid4().hex[:12]}",
                    "amount": amount,
                    "currency": "ZMW",
                    "status": "pay-offline",
                    "mobileMoneyDetails": {
                        "country": country,
                        "phone": phone,
                        "operator": operator,
                    },
                },
            }

        if not self.settings.lenco_api_key:
            raise LencoError("Lenco API key is not configured")

        url = f"{self.settings.lenco_base_url.rstrip('/')}/access/v2/collections/mobile-money"
        payload = {
            "amount": float(amount),
            "reference": reference,
            "phone": phone,
            "operator": operator,
            "country": country,
        }
        headers = {
            "Authorization": f"Bearer {self.settings.lenco_api_key}",
            "Accept": "application/json",
            "User-Agent": "UniStay-API/1.0",
        }
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(url, json=payload, headers=headers)
        return self._handle_response(response, "Lenco mobile-money request failed")

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

    def _handle_response(self, response: httpx.Response, fallback_message: str) -> dict:
        """Parse a Lenco response envelope and raise on provider errors."""
        try:
            body = response.json()
        except Exception as exc:
            raise LencoError(
                f"{fallback_message}: non-JSON response (HTTP {response.status_code})"
            ) from exc

        if response.status_code >= 400:
            message = body.get("message") or fallback_message
            error_code = body.get("errorCode")
            if error_code:
                message = f"{message} (code {error_code})"
            raise LencoError(message, status_code=502)

        # Some error responses return HTTP 200/400 with status=false in the body.
        if body.get("status") is False or body.get("success") is False:
            message = body.get("message") or fallback_message
            error_code = body.get("errorCode")
            if error_code:
                message = f"{message} (code {error_code})"
            raise LencoError(message, status_code=502)

        return body

    async def get_collection_status(self, reference: str) -> dict:
        if self.settings.lenco_mock:
            return {
                "success": True,
                "status": True,
                "message": "Mock collection retrieved",
                "data": {
                    "reference": reference,
                    "lencoReference": None,
                    "amount": "0.00",
                    "currency": "ZMW",
                    "status": "pay-offline",
                },
            }

        if not self.settings.lenco_api_key:
            raise LencoError("Lenco API key is not configured")

        url = f"{self.settings.lenco_base_url.rstrip('/')}/access/v2/collections/status/{reference}"
        headers = {
            "Authorization": f"Bearer {self.settings.lenco_api_key}",
            "Accept": "application/json",
            "User-Agent": "UniStay-API/1.0",
        }
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(url, headers=headers)
        return self._handle_response(response, "Unable to retrieve Lenco collection")
