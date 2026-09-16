from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI(title="BharatRails DPI Control Plane")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-Memory Double-Entry Ledger State
ledger_state = {
    "tax_escrow_balance": 63000.00,
    "supplier_balance": 350000.00,
    "upi_drawdown": 45000.00,
    "mule_status": "CLEARED / ACTIVE",
    "transactions": [
        {"ref": "TXN-INIT-001", "account": "ACC-GST-ESCROW", "amount": 63000.00, "type": "CREDIT"},
        {"ref": "TXN-INIT-002", "account": "ACC-SUPPLIER-PAYABLE", "amount": 350000.00, "type": "CREDIT"}
    ]
}

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>BharatRails Core Initializing... Please refresh in a moment.</h1>"

@app.get("/api/state/metrics")
async def get_metrics():
    return JSONResponse(ledger_state)

@app.post("/api/v1/erp/webhook/erpnext")
async def erp_webhook(request: Request):
    payload = await request.json()
    doc = payload.get("doc", {})
    grand_total = float(doc.get("grand_total", 118000.0))
    inv_num = doc.get("name", "INV-M2M-AUTOMATED")

    # 18% GST Isolation under RBI PA / Nodal Escrow Regulations
    gst_component = round(grand_total * (18 / 118), 2)
    net_supplier = round(grand_total - gst_component, 2)

    ledger_state["tax_escrow_balance"] += gst_component
    ledger_state["supplier_balance"] += net_supplier
    ledger_state["transactions"].append({
        "ref": inv_num,
        "account": "ACC-GST-ESCROW",
        "amount": gst_component,
        "type": "CREDIT"
    })

    return JSONResponse({
        "status": "SETTLED_TO_ESCROW",
        "invoice": inv_num,
        "gst_isolated": gst_component,
        "supplier_net": net_supplier,
        "current_balances": {
            "tax_escrow": ledger_state["tax_escrow_balance"],
            "supplier": ledger_state["supplier_balance"]
        }
    })

@app.post("/api/v1/setu/consent")
async def trigger_consent(request: Request):
    body = await request.json()
    mobile = body.get("mobile", "9999999999")
    consent_id = "c575a370-6308-4b53-a7f0-138f417fba8b"
    return JSONResponse({
        "status": "CONSENT_REQUEST_DISPATCHED",
        "consent_id": consent_id,
        "mobile": mobile,
        "redirect_url": f"https://anumati.setu.co/consent/{consent_id}"
    })

@app.get("/api/v1/setu/financial-data/{consent_id}")
async def get_financial_data(consent_id: str):
    return JSONResponse({
        "consent_id": consent_id,
        "status": "CONSENT_ACTIVE",
        "fip_source": "HDFC0000123",
        "analytics": {
            "avg_monthly_inflow": 482000.0,
            "bounce_rate_pct": 0.0,
            "gst_reconciliation_score": "98.4%",
            "recommended_od_limit": 150000.0
        }
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("gateway:app", host="0.0.0.0", port=8080, reload=True)
