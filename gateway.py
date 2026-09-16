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
async def render_unified_dashboard():
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BharatRails | Institutional Gateway Control Plane</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        .console-font { font-family: 'SF Mono', Monaco, Inconsolata, monospace; font-size: 11px; }
        ::-webkit-scrollbar { width: 5px; height: 5px; }
        ::-webkit-scrollbar-track { background: #0b1329; }
        ::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 4px; }
    </style>
</head>
<body class="bg-slate-950 text-slate-100 flex h-screen overflow-hidden antialiased">
    <aside class="w-64 bg-slate-900 border-r border-slate-800 flex flex-col justify-between flex-shrink-0">
        <div>
            <div class="h-16 flex items-center px-6 border-b border-slate-800 gap-3">
                <div class="w-8 h-8 rounded bg-blue-600 flex items-center justify-center font-bold text-white shadow-lg shadow-blue-500/30">
                    <i class="fa-solid fa-network-wired text-sm"></i>
                </div>
                <div>
                    <span class="font-bold tracking-tight text-white text-base">BHARAT<span class="text-blue-500">RAILS</span></span>
                    <span class="block text-[10px] uppercase tracking-widest text-slate-400 font-semibold">DPI Enterprise Suite</span>
                </div>
            </div>
            <div class="px-4 py-6 space-y-1">
                <div class="px-3 pb-2 text-[10px] font-bold uppercase tracking-wider text-slate-500">External Integrations</div>
                <button onclick="triggerSetuConsent()" class="w-full text-left flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-semibold bg-purple-500/10 text-purple-400 border border-purple-500/20 hover:bg-purple-500/20 transition">
                    <i class="fa-solid fa-file-contract w-4"></i> 1. Setu AA Consent
                </button>
                <button onclick="pullSetuData()" class="w-full text-left flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 hover:bg-indigo-500/20 transition">
                    <i class="fa-solid fa-cloud-arrow-down w-4"></i> 2. Pull Setu AA Data
                </button>
                <div class="pt-3 px-3 pb-2 text-[10px] font-bold uppercase tracking-wider text-slate-500">Simulation Steps</div>
                <button onclick="executeFullPipeline()" class="w-full text-left flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20 transition">
                    <i class="fa-solid fa-play w-4"></i> Run Full Pipeline (1-Click)
                </button>
            </div>
        </div>
        <div class="p-4 border-t border-slate-800">
            <div class="bg-slate-950/70 border border-slate-800 rounded-lg p-3">
                <div class="flex items-center justify-between">
                    <span class="text-[11px] text-slate-400">Status</span>
                    <span class="inline-flex items-center text-[10px] font-bold text-emerald-400">
                        <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 mr-1.5 animate-pulse"></span> ALL WEBHOOKS LIVE
                    </span>
                </div>
                <div class="text-[10px] text-slate-500 font-mono mt-1">Ingress Port :8080</div>
            </div>
        </div>
    </aside>

    <main class="flex-1 flex flex-col overflow-hidden">
        <header class="h-16 border-b border-slate-800 bg-slate-900/50 px-8 flex items-center justify-between flex-shrink-0">
            <div class="flex items-center gap-4">
                <span class="text-xs text-slate-400">Active Webhooks / <span class="text-white font-medium">Zoho, ERPNext, Setu AA, Sandbox.co</span></span>
            </div>
            <div class="flex items-center gap-3">
                <button onclick="pollAll()" class="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-md border border-slate-700 transition">
                    <i class="fa-solid fa-arrows-rotate mr-1"></i> Sync Metrics
                </button>
            </div>
        </header>

        <div class="flex-1 overflow-y-auto p-8 space-y-6">
            <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div class="bg-slate-900 border border-slate-800 rounded-xl p-4">
                    <div class="text-xs text-slate-400">Tax Escrow Holding</div>
                    <div id="metric-tax" class="text-2xl font-bold mt-1 font-mono text-white">₹0.00</div>
                    <div class="text-[11px] text-emerald-400 mt-1"><i class="fa-solid fa-vault"></i> 18% GST Isolated</div>
                </div>
                <div class="bg-slate-900 border border-slate-800 rounded-xl p-4">
                    <div class="text-xs text-slate-400">Supplier Net Balance</div>
                    <div id="metric-supplier" class="text-2xl font-bold mt-1 font-mono text-white">₹0.00</div>
                    <div class="text-[11px] text-blue-400 mt-1"><i class="fa-solid fa-arrow-down"></i> Commercial Settlement</div>
                </div>
                <div class="bg-slate-900 border border-slate-800 rounded-xl p-4">
                    <div class="text-xs text-slate-400">UPI Overdraft Drawn</div>
                    <div id="metric-credit" class="text-2xl font-bold mt-1 font-mono text-amber-400">₹0.00</div>
                    <div class="text-[11px] text-amber-400 mt-1"><i class="fa-solid fa-hand-holding-dollar"></i> Secondary Drawdown</div>
                </div>
                <div class="bg-slate-900 border border-slate-800 rounded-xl p-4">
                    <div class="text-xs text-slate-400">Mule Threat Status</div>
                    <div id="metric-mule" class="text-base font-bold mt-1 font-mono text-emerald-400">HEALTHY</div>
                    <div class="text-[11px] text-slate-500 mt-1"><i class="fa-solid fa-shield-halved"></i> Graph Watchdog</div>
                </div>
            </div>

            <div class="bg-slate-900 border border-slate-800 rounded-xl p-5">
                <div class="flex items-center justify-between pb-3 border-b border-slate-800">
                    <div class="flex items-center gap-2">
                        <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                        <span class="text-xs font-bold uppercase tracking-wider text-slate-300">Live Inbound Webhook & Transaction Stream</span>
                    </div>
                    <button onclick="clearLogs()" class="text-[11px] text-slate-500 hover:text-slate-300">Clear Console</button>
                </div>
                <div id="terminal" class="console-font bg-black/70 rounded-lg p-4 mt-3 h-80 overflow-y-auto text-emerald-400 space-y-1.5 border border-slate-950">
                    <div>[GATEWAY READY] Listening for Zoho, ERPNext, and Setu AA events...</div>
                </div>
            </div>
        </div>
    </main>

    <script>
        let lastConsentId = "";

        async function pollAll() {
            try {
                const res = await fetch('/api/state/metrics');
                const data = await res.json();
                if(data.b2b) {
                    document.getElementById('metric-tax').innerText = '₹' + data.b2b.tax_escrow;
                    document.getElementById('metric-supplier').innerText = '₹' + data.b2b.supplier_payable;
                }
                if(data.upi) {
                    document.getElementById('metric-credit').innerText = '₹' + data.upi.credit_drawn;
                }
                if(data.risk) {
                    const m = document.getElementById('metric-mule');
                    m.innerText = data.risk.mule_status;
                    m.className = data.risk.mule_status === 'LIEN_FREEZE_PLACED' 
                        ? 'text-base font-bold mt-1 font-mono text-rose-400' 
                        : 'text-base font-bold mt-1 font-mono text-emerald-400';
                }
            } catch(e) {}
        }

        async function triggerSetuConsent() {
            log(`>>> INITIATING SETU AA CONSENT (Mobile: 9999999999)...`);
            try {
                const res = await fetch('/api/v1/setu/consent/initiate', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ mobile_number: '9999999999' })
                });
                const data = await res.json();
                lastConsentId = data.consent_id;
                log(`<<< SETU ARTIFACT CREATED [ID: ${data.consent_id}]`);
                log(`>>> ANUMATI URL: ${data.redirect_url}`);
                window.open(data.redirect_url, '_blank');
            } catch (e) {
                log(`!!! SETU ERROR: ${e.message}`);
            }
        }

        async function pullSetuData() {
            if(!lastConsentId) {
                log(`!!! WARNING: No consent ID generated yet. Click "1. Setu AA Consent" first.`);
                return;
            }
            log(`>>> PULLING FINANCIAL DATA ARTIFACTS FOR CONSENT: ${lastConsentId}...`);
            try {
                const res = await fetch(`/api/v1/setu/data/fetch?consent_id=${lastConsentId}`);
                const data = await res.json();
                log(`<<< FINANCIAL DATA RECEIVED FROM SETU:\\n` + JSON.stringify(data, null, 2));
            } catch(e) {
                log(`!!! PULL FAILED: ${e.message}`);
            }
        }

        async function executeFullPipeline() {
            log(`>>> DISPATCHING FULL INSTITUTIONAL SUITE PIPELINE...`);
            await fetch('/api/b2b/test');
            await fetch('/api/upi/test');
            await fetch('/api/risk/test');
            pollAll();
            log(`<<< PIPELINE COMPLETE.`);
        }

        function log(txt) {
            const term = document.getElementById('terminal');
            const row = document.createElement('div');
            row.className = 'whitespace-pre-wrap';
            row.innerText = `[${new Date().toISOString().slice(11,19)}] ${txt}`;
            term.appendChild(row);
            term.scrollTop = term.scrollHeight;
        }

        function clearLogs() {
            document.getElementById('terminal').innerHTML = '<div>[TERMINAL RESET] Ready.</div>';
        }

        setInterval(pollAll, 3000);
        pollAll();
    </script>
</body>
</html>"""

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
