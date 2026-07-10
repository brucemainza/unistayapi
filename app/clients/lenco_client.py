"""Async client for the Lenco collections API."""

from uuid import uuid4

import httpx

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
            "bearer": "merchant",
        }
        headers = {"Authorization": f"Bearer {self.settings.lenco_api_key}"}
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, json=payload, headers=headers)
        if response.status_code >= 400:
            raise LencoError("Lenco mobile-money request failed")
        return response.json()

    async def get_collection_status(self, reference: str) -> dict:
        if self.settings.lenco_mock:
            return {
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
        headers = {"Authorization": f"Bearer {self.settings.lenco_api_key}"}
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, headers=headers)
        if response.status_code >= 400:
            raise LencoError("Unable to retrieve Lenco collection")
        return response.json()
