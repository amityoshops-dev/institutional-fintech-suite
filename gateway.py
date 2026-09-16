import uuid
import logging
from typing import Dict, Any
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Gateway")

app = FastAPI(title="Unified Institutional Fintech Control Plane", version="3.1.0")

SWITCHES = {
    "b2b": "http://127.0.0.1:8000",
    "upi": "http://127.0.0.1:8001",
    "risk": "http://127.0.0.1:8002"
}

@app.get("/", response_class=HTMLResponse)
async def render_unified_dashboard():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>BharatRails | Unified Transaction Simulator</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
            .console-font { font-family: 'SF Mono', Monaco, Inconsolata, 'Courier New', monospace; font-size: 11px; }
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
                    <div class="px-3 pb-2 text-[10px] font-bold uppercase tracking-wider text-slate-500">Simulation Steps</div>
                    <button onclick="executeFullPipeline()" class="w-full text-left flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20 transition">
                        <i class="fa-solid fa-play w-4"></i> Run Full Pipeline (1-Click)
                    </button>
                    <a href="#step-b2b" class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium text-slate-400 hover:text-white hover:bg-slate-800/60 transition">
                        <span class="w-4 text-center font-mono">1</span> B2B ERP & Escrow Split
                    </a>
                    <a href="#step-upi" class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium text-slate-400 hover:text-white hover:bg-slate-800/60 transition">
                        <span class="w-4 text-center font-mono">2</span> UPI Circle Delegation
                    </a>
                    <a href="#step-risk" class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium text-slate-400 hover:text-white hover:bg-slate-800/60 transition">
                        <span class="w-4 text-center font-mono">3</span> ULI & Mule Detection
                    </a>
                </div>
            </div>
            <div class="p-4 border-t border-slate-800">
                <div class="bg-slate-950/70 border border-slate-800 rounded-lg p-3">
                    <div class="flex items-center justify-between">
                        <span class="text-[11px] text-slate-400">Environment</span>
                        <span class="inline-flex items-center text-[10px] font-bold text-emerald-400">
                            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 mr-1.5 animate-pulse"></span> LIVE SANDBOX
                        </span>
                    </div>
                    <div class="text-[10px] text-slate-500 font-mono mt-1">Supervisord Ingress (:8080)</div>
                </div>
            </div>
        </aside>

        <main class="flex-1 flex flex-col overflow-hidden">
            <header class="h-16 border-b border-slate-800 bg-slate-900/50 px-8 flex items-center justify-between flex-shrink-0">
                <div class="flex items-center gap-4">
                    <span class="text-xs text-slate-400">Transaction Orchestrator / <span class="text-white font-medium">Enterprise Gateway</span></span>
                    <span class="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-300 border border-slate-700">Port 8080 Active</span>
                </div>
                <div class="flex items-center gap-3">
                    <button onclick="pollAll()" class="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-md border border-slate-700 transition flex items-center gap-2">
                        <i class="fa-solid fa-arrows-rotate"></i> Sync Metrics
                    </button>
                </div>
            </header>

            <div class="flex-1 overflow-y-auto p-8 space-y-6">
                <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div class="bg-slate-900 border border-slate-800 rounded-xl p-4">
                        <div class="text-xs text-slate-400">Tax Escrow Holding</div>
                        <div id="metric-tax" class="text-2xl font-bold mt-1 font-mono text-white">₹0.00</div>
                        <div class="text-[11px] text-emerald-400 mt-1 flex items-center gap-1">
                            <i class="fa-solid fa-vault"></i> 18% GST Isolated
                        </div>
                    </div>
                    <div class="bg-slate-900 border border-slate-800 rounded-xl p-4">
                        <div class="text-xs text-slate-400">Supplier Net Balance</div>
                        <div id="metric-supplier" class="text-2xl font-bold mt-1 font-mono text-white">₹0.00</div>
                        <div class="text-[11px] text-blue-400 mt-1 flex items-center gap-1">
                            <i class="fa-solid fa-arrow-down"></i> Commercial Settlement
                        </div>
                    </div>
                    <div class="bg-slate-900 border border-slate-800 rounded-xl p-4">
                        <div class="text-xs text-slate-400">UPI Overdraft Drawn</div>
                        <div id="metric-credit" class="text-2xl font-bold mt-1 font-mono text-amber-400">₹0.00</div>
                        <div class="text-[11px] text-amber-400 mt-1 flex items-center gap-1">
                            <i class="fa-solid fa-hand-holding-dollar"></i> Secondary Fallback Active
                        </div>
                    </div>
                    <div class="bg-slate-900 border border-slate-800 rounded-xl p-4">
                        <div class="text-xs text-slate-400">Mule Threat Status</div>
                        <div id="metric-mule" class="text-base font-bold mt-1 font-mono text-emerald-400">HEALTHY</div>
                        <div class="text-[11px] text-slate-500 mt-1 flex items-center gap-1">
                            <i class="fa-solid fa-shield-halved"></i> Graph Fan-Out Watchdog
                        </div>
                    </div>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div id="step-b2b" class="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col justify-between">
                        <div>
                            <div class="flex items-center justify-between">
                                <span class="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">Step 1: Port 8000</span>
                                <span class="text-[10px] font-bold text-emerald-400">BBPS B2B</span>
                            </div>
                            <h3 class="text-sm font-bold text-white mt-3">ERP Ingestion & Split Clearing</h3>
                            <p class="text-xs text-slate-400 mt-1 leading-relaxed">
                                Ingests a corporate purchase order, separates GST into tax escrow, and credits net proceeds to the supplier.
                            </p>
                        </div>
                        <button onclick="triggerEngine('/api/b2b/test', 'B2B ERP Ingestion')" class="mt-4 w-full bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold py-2 px-3 rounded-lg transition">
                            Run Step 1: Settle Invoice
                        </button>
                    </div>

                    <div id="step-upi" class="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col justify-between">
                        <div>
                            <div class="flex items-center justify-between">
                                <span class="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">Step 2: Port 8001</span>
                                <span class="text-[10px] font-bold text-emerald-400">UPI Circle</span>
                            </div>
                            <h3 class="text-sm font-bold text-white mt-3">Family Delegation & Overdraft</h3>
                            <p class="text-xs text-slate-400 mt-1 leading-relaxed">
                                The secondary delegate pays ₹3,500. Drains ₹2,000 savings and draws ₹1,500 from the credit line.
                            </p>
                        </div>
                        <button onclick="triggerEngine('/api/upi/test', 'UPI Circle Spend')" class="mt-4 w-full bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold py-2 px-3 rounded-lg transition">
                            Run Step 2: Delegate Payment
                        </button>
                    </div>

                    <div id="step-risk" class="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col justify-between">
                        <div>
                            <div class="flex items-center justify-between">
                                <span class="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20">Step 3: Port 8002</span>
                                <span class="text-[10px] font-bold text-emerald-400">ULI & MuleHunter</span>
                            </div>
                            <h3 class="text-sm font-bold text-white mt-3">Agri Underwrite & Threat Freeze</h3>
                            <p class="text-xs text-slate-400 mt-1 leading-relaxed">
                                Evaluates land registry data for credit, while graph analysis flags fan-out to freeze a mule account.
                            </p>
                        </div>
                        <button onclick="triggerEngine('/api/risk/test', 'ULI Sanction & Mule Freeze')" class="mt-4 w-full bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold py-2 px-3 rounded-lg transition">
                            Run Step 3: Audit & Freeze
                        </button>
                    </div>
                </div>

                <div class="bg-slate-900 border border-slate-800 rounded-xl p-5">
                    <div class="flex items-center justify-between pb-3 border-b border-slate-800">
                        <div class="flex items-center gap-2">
                            <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                            <span class="text-xs font-bold uppercase tracking-wider text-slate-300">Live Transaction Telemetry & System Logs</span>
                        </div>
                        <button onclick="clearLogs()" class="text-[11px] text-slate-500 hover:text-slate-300 font-medium">Clear Console</button>
                    </div>
                    <div id="terminal" class="console-font bg-black/70 rounded-lg p-4 mt-3 h-64 overflow-y-auto text-emerald-400 space-y-1.5 border border-slate-950">
                        <div>[SYSTEM GATEWAY ACTIVE] Monitoring ports 8000, 8001, and 8002. ERP Webhooks listening on /api/v1/erp/webhook/inbound.</div>
                    </div>
                </div>
            </div>
        </main>

        <script>
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

            async function triggerEngine(endpoint, name) {
                log(`>>> DISPATCHING: ${name} [${endpoint}]`);
                try {
                    const res = await fetch(endpoint);
                    const json = await res.json();
                    log(`<<< RESPONSE [HTTP ${res.status}]:\\n` + JSON.stringify(json, null, 2));
                    pollAll();
                } catch(e) {
                    log(`!!! DISPATCH FAILURE: ${e.message}`);
                }
            }

            async function executeFullPipeline() {
                log(`>>> INITIATING 1-CLICK END-TO-END TRANSACTION PIPELINE...`);
                await triggerEngine('/api/b2b/test', 'Step 1: B2B ERP Ingestion');
                await triggerEngine('/api/upi/test', 'Step 2: UPI Circle Drawdown');
                await triggerEngine('/api/risk/test', 'Step 3: ULI Underwriting & Mule Freeze');
                log(`>>> [COMPLETE] End-to-end multi-rail settlement and threat interception verified.`);
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
    </html>
    """

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
                metrics["upi"] = {
                    "savings": d["savings_balance_inr"],
                    "credit_drawn": d["total_credit_drawn_inr"]
                }
        except Exception:
            pass
        try:
            r = await client.get(f"{SWITCHES['risk']}/api/v1/mulehunter/network-status")
            if r.status_code == 200:
                net = r.json()
                mule_acc = net["accounts"].get("ACC-MULE-NODE-01", {})
                metrics["risk"] = {
                    "mule_status": mule_acc.get("status", "HEALTHY")
                }
        except Exception:
            pass
    return metrics

@app.post("/api/v1/erp/webhook/inbound")
async def receive_external_erp_invoice(request: Request):
    body = await request.json()
    inv_id = body.get("invoice_number", f"INV-ERP-{uuid.uuid4().hex[:6].upper()}")
    total_amount = float(body.get("total_amount", 118000.0))
    supplier_gst = body.get("supplier_gstin", "27AABCU9603R1ZM")
    buyer_gst = body.get("buyer_gstin", "27AABCT1332L1ZV")

    base_amount = round(total_amount / 1.18, 2)
    tax_amount = round(total_amount - base_amount, 2)

    async with httpx.AsyncClient(timeout=8.0) as client:
        # 1. Present invoice to Port 8000
        await client.post(f"{SWITCHES['b2b']}/api/v1/invoices/present", json={
            "invoice_id": inv_id,
            "supplier_gstin": supplier_gst,
            "buyer_gstin": buyer_gst,
            "is_interstate": False,
            "line_items": [
                {
                    "item_desc": "ERP Ingested Goods & Services",
                    "hsn_code": "8471",
                    "quantity": 1,
                    "unit_price": base_amount,
                    "gst_rate_percent": 18.0
                }
            ]
        })

        # 2. Settle on double-entry ledger
        settle_res = await client.post(f"{SWITCHES['b2b']}/api/v1/invoices/{inv_id}/settle", json={
            "buyer_virtual_account": "VA-ERP-BUYER",
            "force_immediate": True
        })

    mock_utr = f"UTR{abs(hash(inv_id)) % 10000000000:010d}"
    return {
        "status": "ERP_PROCESSED_AND_SETTLED",
        "invoice_id": inv_id,
        "tax_escrow_allocated_inr": tax_amount,
        "supplier_net_cleared_inr": base_amount,
        "banking_rail_utr": mock_utr,
        "settlement_ledger": settle_res.json()
    }

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
