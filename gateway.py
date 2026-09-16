import os
import uuid
import logging
from typing import Dict, Any
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
import httpx
from setu_client import SetuAAClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Gateway")

app = FastAPI(title="Unified Institutional Fintech Control Plane", version="3.3.0")

SWITCHES = {
    "b2b": "http://127.0.0.1:8000",
    "upi": "http://127.0.0.1:8001",
    "risk": "http://127.0.0.1:8002"
}

SANDBOX_CO_API_KEY = os.getenv("SANDBOX_CO_API_KEY", "")

# ---------------------------------------------------------
# SANDBOX.CO.IN REAL GSTIN VALIDATOR
# ---------------------------------------------------------
async def verify_gstin_live(gstin: str) -> Dict[str, Any]:
    if not SANDBOX_CO_API_KEY:
        return {"status": "SKIPPED_NO_KEY", "gstin": gstin, "legal_name": "Simulated Active Taxpayer"}
    
    headers = {
        "x-api-key": SANDBOX_CO_API_KEY,
        "x-api-version": "1.0"
    }
    async with httpx.AsyncClient(timeout=6.0) as client:
        try:
            r = await client.get(f"https://api.sandbox.co.in/gsp/public/gstin/{gstin}", headers=headers)
            if r.status_code == 200:
                data = r.json().get("data", {})
                return {
                    "status": "VERIFIED_LIVE",
                    "legal_name": data.get("lgnm", "Verified Taxpayer"),
                    "taxpayer_type": data.get("dty", "Regular"),
                    "state_code": gstin[:2]
                }
        except Exception:
            pass
    return {"status": "OFFLINE_FALLBACK", "legal_name": "Verified Taxpayer"}

# ---------------------------------------------------------
# FRONTEND CONTROL PLANE
# ---------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/api/state/metrics")
async def get_state_metrics():
    metrics: Dict[str, Any] = {"b2b": None, "upi": None, "risk": None}
    async with httpx.AsyncClient(timeout=2.0) as client:
        try:
            r = await client.get(f"{SWITCHES['b2b']}/api/v1/ledger/accounts")
            if r.status_code == 200:
                accs = {a["account_id"]: a["balance_inr"] for a in r.json()}
                metrics["b2b"] = {
                    "tax_escrow": accs.get("ACC-GST-ESCROW", "0.00"),
                    "supplier_payable": accs.get("ACC-SUPPLIER-PAYABLE", "0.00")
                }
        except Exception:
            pass
        try:
            r = await client.get(f"{SWITCHES['upi']}/api/v1/accounts/parent@bank")
            if r.status_code == 200:
                d = r.json()
                metrics["upi"] = {"savings": d["savings_balance_inr"], "credit_drawn": d["total_credit_drawn_inr"]}
        except Exception:
            pass
        try:
            r = await client.get(f"{SWITCHES['risk']}/api/v1/mulehunter/network-status")
            if r.status_code == 200:
                net = r.json()
                mule_acc = net["accounts"].get("ACC-MULE-NODE-01", {})
                metrics["risk"] = {"mule_status": mule_acc.get("status", "HEALTHY")}
        except Exception:
            pass
    return metrics

# ---------------------------------------------------------
# SETU AA LIVE ENDPOINTS
# ---------------------------------------------------------
@app.post("/api/v1/setu/consent/initiate")
async def initiate_setu_consent(request: Request):
    body = await request.json()
    mobile = body.get("mobile_number", "9999999999")
    vua = body.get("vua_handle", None)
    res = await SetuAAClient.create_consent_request(mobile, vua)
    return JSONResponse(content=res)

@app.get("/api/v1/setu/callback")
async def setu_consent_callback(request: Request):
    params = dict(request.query_params)
    return {
        "status": "SETU_CONSENT_APPROVED",
        "details": params,
        "message": "Consent successfully granted. You can now click '2. Pull Setu AA Data'."
    }

@app.get("/api/v1/setu/data/fetch")
async def fetch_setu_data(consent_id: str):
    data = await SetuAAClient.fetch_financial_data(consent_id)
    return JSONResponse(content=data)

# ---------------------------------------------------------
# 1. ZOHO BOOKS WEBHOOK INGESTION
# ---------------------------------------------------------
@app.post("/api/v1/erp/webhook/zoho")
async def receive_zoho_webhook(request: Request):
    payload = await request.json()
    invoice_data = payload.get("invoice", payload)
    
    inv_id = invoice_data.get("invoice_number", f"ZOHO-{uuid.uuid4().hex[:6].upper()}")
    total_amount = float(invoice_data.get("total", 59000.0))
    supplier_gst = invoice_data.get("gst_treatment", "27AABCU9603R1ZM")
    buyer_gst = invoice_data.get("shipping_address", {}).get("gst_no", "27AABCT1332L1ZV")

    # Live GST validation via Sandbox.co.in
    gst_val = await verify_gstin_live(supplier_gst)

    base_amount = round(total_amount / 1.18, 2)
    tax_amount = round(total_amount - base_amount, 2)

    async with httpx.AsyncClient(timeout=8.0) as client:
        await client.post(f"{SWITCHES['b2b']}/api/v1/invoices/present", json={
            "invoice_id": inv_id,
            "supplier_gstin": supplier_gst,
            "buyer_gstin": buyer_gst,
            "is_interstate": False,
            "line_items": [{"item_desc": "Zoho Invoice Item", "hsn_code": "8471", "quantity": 1, "unit_price": base_amount, "gst_rate_percent": 18.0}]
        })
        settle_res = await client.post(f"{SWITCHES['b2b']}/api/v1/invoices/{inv_id}/settle", json={
            "buyer_virtual_account": "VA-ZOHO-CORP",
            "force_immediate": True
        })

    return {
        "status": "ZOHO_INVOICE_PROCESSED",
        "invoice_id": inv_id,
        "tax_escrow_allocated_inr": tax_amount,
        "supplier_net_cleared_inr": base_amount,
        "gst_portal_verification": gst_val,
        "settlement_ledger": settle_res.json()
    }

# ---------------------------------------------------------
# 2. ERPNEXT WEBHOOK INGESTION
# ---------------------------------------------------------
@app.post("/api/v1/erp/webhook/erpnext")
async def receive_erpnext_webhook(request: Request):
    payload = await request.json()
    doc = payload.get("doc", payload)

    inv_id = doc.get("name", f"ERPNEXT-{uuid.uuid4().hex[:6].upper()}")
    total_amount = float(doc.get("grand_total", 118000.0))
    supplier_gst = doc.get("company_gstin", "27AABCU9603R1ZM")
    buyer_gst = doc.get("billing_address_gstin", "27AABCT1332L1ZV")

    base_amount = round(total_amount / 1.18, 2)
    tax_amount = round(total_amount - base_amount, 2)

    async with httpx.AsyncClient(timeout=8.0) as client:
        await client.post(f"{SWITCHES['b2b']}/api/v1/invoices/present", json={
            "invoice_id": inv_id,
            "supplier_gstin": supplier_gst,
            "buyer_gstin": buyer_gst,
            "is_interstate": False,
            "line_items": [{"item_desc": "ERPNext Goods", "hsn_code": "8471", "quantity": 1, "unit_price": base_amount, "gst_rate_percent": 18.0}]
        })
        settle_res = await client.post(f"{SWITCHES['b2b']}/api/v1/invoices/{inv_id}/settle", json={
            "buyer_virtual_account": "VA-ERPNEXT-CORP",
            "force_immediate": True
        })

    return {
        "status": "ERPNEXT_PROCESSED",
        "invoice_id": inv_id,
        "tax_escrow_allocated_inr": tax_amount,
        "supplier_net_cleared_inr": base_amount,
        "settlement_ledger": settle_res.json()
    }

# ---------------------------------------------------------
# STANDALONE TEST SIMULATORS
# ---------------------------------------------------------
@app.get("/api/b2b/test")
async def run_b2b():
    async with httpx.AsyncClient(timeout=5.0) as client:
        inv_id = f"INV-B2B-{uuid.uuid4().hex[:6].upper()}"
        await client.post(f"{SWITCHES['b2b']}/api/v1/invoices/present", json={
            "invoice_id": inv_id,
            "supplier_gstin": "27AABCU9603R1ZM",
            "buyer_gstin": "27AABCT1332L1ZV",
            "is_interstate": False,
            "line_items": [{"item_desc": "Hardware Server Rack", "hsn_code": "8471", "quantity": 1, "unit_price": 50000.0, "gst_rate_percent": 18.0}]
        })
        res = await client.post(f"{SWITCHES['b2b']}/api/v1/invoices/{inv_id}/settle", json={
            "buyer_virtual_account": "VA-CORP-AUTO",
            "force_immediate": True
        })
        return res.json()

@app.get("/api/upi/test")
async def run_upi():
    async with httpx.AsyncClient(timeout=5.0) as client:
        res = await client.get(f"{SWITCHES['upi']}/api/v1/circle/test/run-all")
        return res.json()

@app.get("/api/risk/test")
async def run_risk():
    async with httpx.AsyncClient(timeout=5.0) as client:
        res = await client.get(f"{SWITCHES['risk']}/api/v1/system/test/run-all")
        return res.json()
