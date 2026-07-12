#!/usr/bin/env python3
"""Quick smoke-test script for a UniStay Render deploy.

Usage:
    python scripts/render_deploy_check.py https://unistay-api.onrender.com

Without a BASE_URL argument the script defaults to ``http://localhost:8000``.
"""

import asyncio
import json
import random
import sys

import httpx


async def check(base: str):
    async with httpx.AsyncClient(base_url=base, timeout=15) as client:

        async def call(method: str, path: str, *, body=None, headers=None) -> tuple[int, dict]:
            kwargs = {"headers": headers or {}}
            if body is not None:
                kwargs["json"] = body
            r = {"GET": client.get, "POST": client.post}[method](path, **kwargs)
            res = await r
            try:
                data = res.json()
            except Exception:
                data = {"raw": res.text[:500]}
            return res.status_code, data

        pad = "  "

        # ── 1. Health ──
        status, body = await call("GET", "/api/health")
        ok = body.get("status") is True
        print(f"{'✅' if ok else '❌'} GET /api/health → {status} — {json.dumps(body.get('data', body), default=str)}")

        # ── 2. OpenAPI ──
        status, body = await call("GET", "/openapi.json")
        ok = status == 200
        print(f"{'✅' if ok else '❌'} GET /openapi.json → {status} {'— OK' if ok else ''}")

        # ── 3. Register student ──
        suffix = random.randint(1_000_000_000, 9_999_999_999)
        payload = {"full_name": f"Smoke {suffix}", "phone": str(suffix), "email": f"smoke_{suffix}@test.com", "password": "test123", "role": "student"}
        status, body = await call("POST", "/api/auth/register", body=payload)
        ok = status == 200 and body.get("status") is True
        token = body.get("data", {}).get("token", "") if ok else ""
        print(f"{'✅' if ok else '❌'} POST /api/auth/register → {status} — {body.get('message', body)}")

        # ── 4. Login ──
        status, body = await call("POST", "/api/auth/login", body={"phone": payload["phone"], "password": "test123"})
        ok = status == 200
        print(f"{'✅' if ok else '❌'} POST /api/auth/login → {status}")

        # ── 5. Auth me ──
        if token:
            status, body = await call("GET", "/api/auth/me", headers={"Authorization": f"Bearer {token}"})
            ok = status == 200
            print(f"{'✅' if ok else '❌'} GET /api/auth/me → {status}")
        else:
            print(f"{pad}⚠️  Skipped (no token)")

        # ── 6. Universities ──
        status, body = await call("GET", "/api/universities")
        ok = status == 200
        count = len(body.get("data", [])) if ok else 0
        print(f"{'✅' if ok else '❌'} GET /api/universities → {status} — {count} universities")

        # ── 7. Houses ──
        status, body = await call("GET", "/api/houses")
        ok = status == 200
        data = body.get("data")
        count = len(data) if isinstance(data, list) else 0
        print(f"{'✅' if ok else '❌'} GET /api/houses → {status} — {count} houses")

        # ── 8. Places autocomplete (needs GOOGLE_MAPS_SERVER_KEY) ──
        status, body = await call("GET", "/api/places/autocomplete?input=Lusaka&session_token=smoke")
        ok = status == 200
        print(f"{'✅' if ok else '⚠️'} GET /api/places/autocomplete → {status} — {'OK' if ok else 'Google Maps may not be configured'}")

        print("\nDone. If all ✅ the Render deploy is ready for the mobile app.")


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    print(f"UniStay deploy check — {base}\n")
    asyncio.run(check(base))


if __name__ == "__main__":
    main()