"""
Unified Institutional Gateway & Executive Dashboard
Aggregates Port 8000 (B2B Settlement), Port 8001 (UPI Circle), and Port 8002 (ULI & MuleHunter)
"""
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import httpx
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Gateway")

app = FastAPI(title="Unified Institutional Fintech Gateway", version="1.0.0")

SWITCHES = {
    "b2b": "http://127.0.0.1:8000",
    "upi": "http://127.0.0.1:8001",
    "risk": "http://127.0.0.1:8002"
}

@app.get("/", response_class=HTMLResponse)
async def render_dashboard():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Institutional Fintech Control Plane</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            .log-stream { font-family: 'Courier New', monospace; font-size: 0.82rem; }
        </style>
    </head>
    <body class="bg-slate-950 text-slate-100 min-h-screen p-6">
        <div class="max-w-7xl mx-auto space-y-6">
            <!-- Header -->
            <header class="flex justify-between items-center border-b border-slate-800 pb-4">
                <div>
                    <h1 class="text-2xl font-bold tracking-tight text-white">Institutional DPI Orchestration Suite</h1>
                    <p class="text-sm text-slate-400">Production Control Plane: BBPS B2B | UPI Circle | ULI & MuleHunter.AI</p>
                </div>
                <div class="flex items-center space-x-2">
                    <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        <span class="w-2 h-2 rounded-full bg-emerald-400 mr-2 animate-pulse"></span>
                        GATEWAY ACTIVE (PORT 8080)
                    </span>
                </div>
            </header>

            <!-- Live Engine Cards -->
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                <!-- Engine 1 -->
                <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col justify-between shadow-xl">
                    <div>
                        <div class="flex items-center justify-between">
                            <span class="text-xs font-bold uppercase tracking-wider text-indigo-400">Port 8000</span>
                            <span id="badge-b2b" class="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300">Checking...</span>
                        </div>
                        <h2 class="text-lg font-semibold mt-2">B2B Settlement & Agentic Concierge</h2>
                        <p class="text-xs text-slate-400 mt-1">Double-entry split escrow, GST allocation & autonomous POD logistics mediation.</p>
                        <div class="mt-4 space-y-2 text-xs">
                            <div class="flex justify-between py-1 border-b border-slate-800/60">
                                <span class="text-slate-500">Tax Escrow (Paise):</span>
                                <span id="val-tax" class="font-mono text-slate-200">--</span>
                            </div>
                            <div class="flex justify-between py-1 border-b border-slate-800/60">
                                <span class="text-slate-500">Supplier Net Payouts:</span>
                                <span id="val-supplier" class="font-mono text-slate-200">--</span>
                            </div>
                        </div>
                    </div>
                    <button onclick="triggerEngine('/api/b2b/test', 'b2b-log')" class="mt-4 w-full bg-indigo-600 hover:bg-indigo-500 text-white font-medium py-2 px-3 rounded-lg text-xs transition duration-150">
                        Run Split Settlement Test
                    </button>
                </div>

                <!-- Engine 2 -->
                <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col justify-between shadow-xl">
                    <div>
                        <div class="flex items-center justify-between">
                            <span class="text-xs font-bold uppercase tracking-wider text-cyan-400">Port 8001</span>
                            <span id="badge-upi" class="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300">Checking...</span>
                        </div>
                        <h2 class="text-lg font-semibold mt-2">UPI Circle & Overdraft Switch</h2>
                        <p class="text-xs text-slate-400 mt-1">Delegated family payment rules, monthly spend quotas & credit line drawdowns.</p>
                        <div class="mt-4 space-y-2 text-xs">
                            <div class="flex justify-between py-1 border-b border-slate-800/60">
                                <span class="text-slate-500">Parent Savings:</span>
                                <span id="val-savings" class="font-mono text-slate-200">--</span>
                            </div>
                            <div class="flex justify-between py-1 border-b border-slate-800/60">
                                <span class="text-slate-500">Credit Line Drawn:</span>
                                <span id="val-credit" class="font-mono text-amber-400">--</span>
                            </div>
                        </div>
                    </div>
                    <button onclick="triggerEngine('/api/upi/test', 'upi-log')" class="mt-4 w-full bg-cyan-600 hover:bg-cyan-500 text-white font-medium py-2 px-3 rounded-lg text-xs transition duration-150">
                        Run Circle Delegation Test
                    </button>
                </div>

                <!-- Engine 3 -->
                <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col justify-between shadow-xl">
                    <div>
                        <div class="flex items-center justify-between">
                            <span class="text-xs font-bold uppercase tracking-wider text-rose-400">Port 8002</span>
                            <span id="badge-risk" class="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300">Checking...</span>
                        </div>
                        <h2 class="text-lg font-semibold mt-2">ULI & MuleHunter.AI Guardrail</h2>
                        <p class="text-xs text-slate-400 mt-1">Multi-registry agri-scoring & real-time topological transaction lien placement.</p>
                        <div class="mt-4 space-y-2 text-xs">
                            <div class="flex justify-between py-1 border-b border-slate-800/60">
                                <span class="text-slate-500">Graph Monitored Nodes:</span>
                                <span id="val-nodes" class="font-mono text-slate-200">--</span>
                            </div>
                            <div class="flex justify-between py-1 border-b border-slate-800/60">
                                <span class="text-slate-500">Mule Account Status:</span>
                                <span id="val-mule" class="font-mono text-rose-400 font-bold">--</span>
                            </div>
                        </div>
                    </div>
                    <button onclick="triggerEngine('/api/risk/test', 'risk-log')" class="mt-4 w-full bg-rose-600 hover:bg-rose-500 text-white font-medium py-2 px-3 rounded-lg text-xs transition duration-150">
                        Run ULI Sanction & Mule Freeze
                    </button>
                </div>
            </div>

            <!-- Real-Time Telemetry & Console Log Terminal -->
            <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-2xl">
                <div class="flex items-center justify-between pb-3 border-b border-slate-800">
                    <span class="text-sm font-semibold flex items-center gap-2">
                        <span class="h-2 w-2 rounded-full bg-emerald-500"></span> Live Telemetry Terminal
                    </span>
                    <button onclick="clearConsole()" class="text-xs text-slate-500 hover:text-slate-300">Clear Terminal</button>
                </div>
                <div id="terminal" class="log-stream bg-black/80 rounded-lg p-4 mt-3 h-64 overflow-y-auto text-emerald-400 border border-slate-900 space-y-1">
                    <div>[SYSTEM GATEWAY READY] Listening for institutional telemetry events...</div>
                </div>
            </div>
        </div>

        <script>
            async function updateHealth() {
                try {
                    const res = await fetch('/api/health');
                    const data = await res.json();
                    
                    document.getElementById('badge-b2b').innerText = data.b2b ? 'HEALTHY' : 'DOWN';
                    document.getElementById('badge-b2b').className = data.b2b ? 'text-xs px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400' : 'text-xs px-2 py-0.5 rounded bg-rose-500/20 text-rose-400';

                    document.getElementById('badge-upi').innerText = data.upi ? 'HEALTHY' : 'DOWN';
                    document.getElementById('badge-upi').className = data.upi ? 'text-xs px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400' : 'text-xs px-2 py-0.5 rounded bg-rose-500/20 text-rose-400';

                    document.getElementById('badge-risk').innerText = data.risk ? 'HEALTHY' : 'DOWN';
                    document.getElementById('badge-risk').className = data.risk ? 'text-xs px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400' : 'text-xs px-2 py-0.5 rounded bg-rose-500/20 text-rose-400';
                } catch(e) {}
            }

            async function triggerEngine(url, label) {
                log(`>>> Dispatched trigger: ${url}`);
                try {
                    const res = await fetch(url);
                    const json = await res.json();
                    log(`<<< Response [${res.status}]: ${JSON.stringify(json, null, 2)}`);
                    pollState();
                } catch (e) {
                    log(`!!! Error dispatching request: ${e.message}`);
                }
            }

            async function pollState() {
                try {
                    const res = await fetch('/api/state/metrics');
                    const m = await res.json();
                    if(m.b2b) {
                        document.getElementById('val-tax').innerText = '₹' + m.b2b.tax_escrow;
                        document.getElementById('val-supplier').innerText = '₹' + m.b2b.supplier_payable;
                    }
                    if(m.upi) {
                        document.getElementById('val-savings').innerText = '₹' + m.upi.savings;
                        document.getElementById('val-credit').innerText = '₹' + m.upi.credit_drawn;
                    }
                    if(m.risk) {
                        document.getElementById('val-nodes').innerText = m.risk.total_nodes;
                        document.getElementById('val-mule').innerText = m.risk.mule_status;
                    }
                } catch(e) {}
            }

            function log(msg) {
                const term = document.getElementById('terminal');
                const line = document.createElement('div');
                line.innerText = `[${new Date().toISOString().split('T')[1].slice(0,8)}] ${msg}`;
                term.appendChild(line);
                term.scrollTop = term.scrollHeight;
            }

            function clearConsole() {
                document.getElementById('terminal').innerHTML = '<div>[TERMINAL RESET]</div>';
            }

            setInterval(updateHealth, 4000);
            updateHealth();
            pollState();
        </script>
    </body>
    </html>
    """

@app.get("/api/health")
async def health_check():
    health = {}
    async with httpx.AsyncClient(timeout=2.0) as client:
        for name, base_url in SWITCHES.items():
            try:
                r = await client.get(f"{base_url}/docs")
                health[name] = (r.status_code == 200)
            except Exception:
                health[name] = False
    return health

@app.get("/api/state/metrics")
async def get_state_metrics():
    metrics = {"b2b": None, "upi": None, "risk": None}
    async with httpx.AsyncClient(timeout=2.5) as client:
        # B2B accounts
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

        # UPI balances
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

        # Risk balances
        try:
            r = await client.get(f"{SWITCHES['risk']}/api/v1/mulehunter/network-status")
            if r.status_code == 200:
                net = r.json()
                mule_acc = net["accounts"].get("ACC-MULE-NODE-01", {})
                metrics["risk"] = {
                    "total_nodes": net.get("total_nodes", 0),
                    "mule_status": mule_acc.get("status", "UNKNOWN")
                }
        except Exception:
            pass

    return metrics

# Test Dispatch Relays
@app.get("/api/b2b/test")
async def run_b2b_proxy():
    async with httpx.AsyncClient(timeout=5.0) as client:
        r = await client.post(f"{SWITCHES['b2b']}/api/v1/invoices/present", json={
            "invoice_id": f"INV-AUTO-{httpx._utils.get_environment_proxies}",
            "supplier_gstin": "27AABCU9603R1ZM",
            "buyer_gstin": "27AABCT1332L1ZV",
            "is_interstate": False,
            "line_items": [{"item_desc": "Industrial Switch Blade", "hsn_code": "8537", "quantity": 1, "unit_price": 50000.0, "gst_rate_percent": 18.0}]
        })
        # Settle right away
        inv_id = r.json().get("invoice_id")
        if inv_id:
            s = await client.post(f"{SWITCHES['b2b']}/api/v1/invoices/{inv_id}/settle", json={"buyer_virtual_account": "VA-CORP-AUTO", "force_immediate": True})
            return s.json()
        return r.json()

@app.get("/api/upi/test")
async def run_upi_proxy():
    async with httpx.AsyncClient(timeout=5.0) as client:
        r = await client.get(f"{SWITCHES['upi']}/api/v1/circle/test/run-all")
        return r.json()

@app.get("/api/risk/test")
async def run_risk_proxy():
    async with httpx.AsyncClient(timeout=5.0) as client:
        r = await client.get(f"{SWITCHES['risk']}/api/v1/system/test/run-all")
        return r.json()