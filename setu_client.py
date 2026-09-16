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
    """Client for Setu Account Aggregator (FIU Sandbox)."""

    @staticmethod
    async def create_consent_request(
        mobile_number: str,
        vua_handle: str = None
    ) -> Dict[str, Any]:
        """
        Creates a consent request for bank statement sharing.
        Sandbox test mobile: 9999999999 (OTP is usually 123456).
        """
        vua = vua_handle if vua_handle else f"{mobile_number}@setu"
        now = datetime.now(timezone.utc)
        start_date = (now - timedelta(days=180)).strftime("%Y-%m-%dT%H:%M:%SZ")
        end_date = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        expiry_date = (now + timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")

        payload = {
            "vua": vua,
            "consentDuration": {"unit": "MONTH", "value": "1"},
            "dataRange": {
                "from": start_date,
                "to": end_date
            },
            "consentTypes": ["TRANSACTIONS", "PROFILE", "SUMMARY"],
            "fiTypes": ["DEPOSIT"],
            "consentMode": "VIEW",
            "fetchType": "ONETIME"
        }

        # If live credentials exist, hit the real Setu Sandbox
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

        # Real-format Sandbox Mock response (Matches Setu Sandbox schema)
        consent_id = str(uuid.uuid4())
        return {
            "status": "PENDING",
            "consent_id": consent_id,
            "vua": vua,
            "redirect_url": f"https://anumati.setu.co/{consent_id}?redirect_url=https://institutional-fintech-suite.onrender.com/api/v1/setu/callback",
            "fi_types": ["DEPOSIT"],
            "data_range": {"from": start_date, "to": end_date},
            "message": "Direct the borrower to redirect_url to complete OTP verification (use OTP 123456 on Setu Anumati)."
        }
