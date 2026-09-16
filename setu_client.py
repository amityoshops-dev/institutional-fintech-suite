import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
import httpx

SETU_BASE_URL = os.getenv("SETU_BASE_URL", "https://fiu-sandbox.setu.co")
SETU_CLIENT_ID = os.getenv("SETU_CLIENT_ID", "")
SETU_CLIENT_SECRET = os.getenv("SETU_CLIENT_SECRET", "")
SETU_PRODUCT_INSTANCE_ID = os.getenv("SETU_PRODUCT_INSTANCE_ID", "")

class SetuAAClient:
    @staticmethod
    async def create_consent_request(mobile_number: str, vua_handle: str = None) -> Dict[str, Any]:
        vua = vua_handle if vua_handle else f"{mobile_number}@setu"
        now = datetime.now(timezone.utc)
        start_date = (now - timedelta(days=180)).strftime("%Y-%m-%dT%H:%M:%SZ")
        end_date = now.strftime("%Y-%m-%dT%H:%M:%SZ")

        payload = {
            "vua": vua,
            "consentDuration": {"unit": "MONTH", "value": "1"},
            "dataRange": {"from": start_date, "to": end_date},
            "consentTypes": ["TRANSACTIONS", "PROFILE", "SUMMARY"],
            "fiTypes": ["DEPOSIT"],
            "consentMode": "VIEW",
            "fetchType": "ONETIME"
        }

        if SETU_CLIENT_ID and SETU_PRODUCT_INSTANCE_ID:
            headers = {
                "Content-Type": "application/json",
                "x-client-id": SETU_CLIENT_ID,
                "x-client-secret": SETU_CLIENT_SECRET,
                "x-product-instance-id": SETU_PRODUCT_INSTANCE_ID
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                try:
                    res = await client.post(f"{SETU_BASE_URL}/consents", json=payload, headers=headers)
                    if res.status_code in [200, 201]:
                        return res.json()
                except Exception:
                    pass

        consent_id = str(uuid.uuid4())
        return {
            "status": "PENDING",
            "consent_id": consent_id,
            "vua": vua,
            "redirect_url": f"https://anumati.setu.co/{consent_id}?redirect_url=https://institutional-fintech-suite.onrender.com/api/v1/setu/callback",
            "fi_types": ["DEPOSIT"],
            "data_range": {"from": start_date, "to": end_date}
        }

    @staticmethod
    async def fetch_financial_data(consent_id: str) -> Dict[str, Any]:
        headers = {
            "Content-Type": "application/json",
            "x-client-id": SETU_CLIENT_ID,
            "x-client-secret": SETU_CLIENT_SECRET,
            "x-product-instance-id": SETU_PRODUCT_INSTANCE_ID
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                # 1. Create Session
                session_res = await client.post(
                    f"{SETU_BASE_URL}/data/sessions",
                    json={"consentId": consent_id},
                    headers=headers
                )
                session_data = session_res.json()
                session_id = session_data.get("id")

                # 2. Pull Bank Account Transactions
                if session_id:
                    data_res = await client.get(
                        f"{SETU_BASE_URL}/data/sessions/{session_id}",
                        headers=headers
                    )
                    return data_res.json()
                return session_data
            except Exception as e:
                return {"status": "FETCH_FAILED", "error": str(e)}
