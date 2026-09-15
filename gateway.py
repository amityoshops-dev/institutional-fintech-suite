import httpx
import logging
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Gateway")

app = FastAPI(title="Institutional Fintech Gateway", version="2.0.0")

SWITCHES = {
    "b2b": "http://127.0.0.1:8000",
    "upi": "http://127.0.0.1:8001",
    "risk": "http://127.0.0.1:8002"
}

@app.get("/", response_class=HTMLResponse)
async def render_dashboard():
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BharatRails | Institutional Switch Control Plane</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    colors: {
                        rzp: {
                            dark: '#0c1322',
                            sidebar: '#080d1a',
                            card: '#11192c',
                            border: '#1e293b',
                            blue: '#3395ff',
                            blueHover: '#207df3',
                            green: '#10b981',
                            alert: '#ef4444',
                            textMuted: '#8b9fc3'
                        }
                    }
                }
            }
        }
    </script>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        .terminal-font { font-family: 'SF Mono', Monaco, Inconsolata, 'Courier New', monospace; font-size: 11px; }
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: #080d1a; }
        ::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 3px; }
    </style>
</head>
<body class="bg-rzp-dark text-slate-100 flex h-screen overflow-hidden antialiased">
    <aside class="w-64 bg-rzp-sidebar border-r border-rzp-border flex flex-col justify-between flex-shrink-0">
        <div>
            <div class="h-16 flex items-center px-6 border-b border-rzp-border gap-3">
                <div class="w-8 h-8 rounded bg-rzp-blue flex items-center justify-center font-bold text-white shadow-lg shadow-blue-500/30">
                    <i class="fa-solid fa-bolt text-sm"></i>
                </div>
                <div>
                    <span class="font-bold tracking-tight text-white text-base">BHARAT<span class="text-rzp-blue">RAILS</span></span>
                    <span class="block text-[10px] uppercase tracking-widest text-rzp-textMuted font-semibold">Institutional Switch</span>
                </div>
            </div>
            <div class="px-3 py-6 space-y-1">
                <div class="px-3 pb-2 text-[10px] font-bold uppercase tracking-wider text-slate-500">Core Switches</div>
                <a href="#" class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-semibold bg-rzp-blue/10 text-rzp-blue border border-rzp-blue/20">
                    <i class="fa-solid fa-layer-group w-4"></i> Overview Dashboard
                </a>
                <a href="#b2b-section" class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium text-rzp-textMuted hover:text-white hover:bg-slate-800/40 transition">
                    <i class="fa-solid fa-file-invoice-dollar w-4"></i> Bharat Connect (B2B)
                </a>
                <a href="#upi-section" class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium text-rzp-textMuted hover:text-white hover:bg-slate-800/40 transition">
                    <i class="fa-solid fa-circle-nodes w-4"></i> UPI Circle & Overdraft
                </a>
                <a href="#risk-section" class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium text-rzp-textMuted hover:text-white hover:bg-slate-800/40 transition">
                    <i class="fa-solid fa-shield-halved w-4"></i> MuleHunter.AI & ULI
                </a>
            </div>
        </div>
        <div class="p-4 border-t border-rzp-border">
            <div class="bg-slate-900/80 border border-rzp-border rounded-lg p-3">
                <div class="flex items-center justify-between">
                    <span class="text-[11px] text-rzp-textMuted">Environment</span>
                    <span class="inline-flex items-center text-[10px] font-bold text-rzp-green">
                        <span class="w-1.5 h-1.5 rounded-full bg-rzp-green mr-1.5 animate-pulse"></span> LIVE SANDBOX
                    </span>
                </div>
                <div class="text-[10px] text-slate-500 font-mono mt-1">Supervisord Orchestrated</div>
            </div>
        </div>
    </aside>
    <main class="flex-1 flex flex-col overflow-hidden">
        <header class="h-16 border-b border-rzp-border bg-rzp-sidebar/50 px-8 flex items-center justify-between flex-shrink-0">
            <div class="flex items-center gap-4">
                <span class="text-xs text-slate-400">Institutional Gateway / <span class="text-white font-medium">Control Plane</span></span>
                <span class="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-300 border border-slate-700">Port 8080 Active</span>
            </div>
            <div class="flex items-center gap-3">
                <button onclick="pollAll()" class="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-md border border-slate-700 transition flex items-center gap-2">
                    <i class="fa-solid fa-arrows-rotate"></i> Sync State
                </button>
                <div class="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-xs text-slate-300 font-bold">
                    IN
                </div>
            </div>
        </header>
        <div class="flex-1 overflow-y-auto p-8 space-y-8">
            <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div class="bg-rzp-card border border-rzp-border rounded-xl p-4 shadow-sm">
                    <div class="text-xs text-rzp-textMuted font-medium">Tax Escrow Balance</div>
                    <div id="metric-tax" class="text-2xl font-bold mt-1 font-mono text-white">₹0.00</div>
                    <div class="text-[11px] text-slate-500 mt-1 flex items-center gap-1">
                        <i class="fa-solid fa-lock text-emerald-400"></i> GST Holding Escrow (BBPS B2B)
                    </div>
                </div>
                <div class="bg-rzp-card border border-rzp-border rounded-xl p-4 shadow-sm">
                    <div class="text-xs text-rzp-textMuted font-medium">Supplier Payables</div>
                    <div id="metric-supplier" class="text-2xl font-bold mt-1 font-mono text-white">₹0.00</div>
                    <div class="text-[11px] text-slate-500 mt-1 flex items-center gap-1">
                        <i class="fa-solid fa-arrow-down-long text-blue-400"></i> Unencumbered Node
                    </div>
                </div>
                <div class="bg-rzp-card border border-rzp-border rounded-xl p-4 shadow-sm">
                    <div class="text-xs text-rzp-textMuted font-medium">Overdraft Credit Drawn</div>
                    <div id="metric-credit" class="text-2xl font-bold mt-1 font-mono text-amber-400">₹0.00</div>
                    <div class="text-[11px] text-slate-500 mt-1 flex items-center gap-1">
                        <i class="fa-solid fa-credit-card text-amber-400"></i> UPI Circle Automatic Drawdown
                    </div>
                </div>
                <div class="bg-rzp-card border border-rzp-border rounded-xl p-4 shadow-sm">
                    <div class="text-xs text-rzp-textMuted font-medium">Mule Threat State</div>
                    <div id="metric-mule" class="text-lg font-bold mt-1 font-mono text-emerald-400">MONITORING</div>
                    <div class="text-[11px] text-slate-500 mt-1 flex items-center gap-1">
                        <i class="fa-solid fa-shield-virus text-rose-400"></i> MuleHunter.AI Fan-Out Guard
                    </div>
                </div>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div id="b2b-section" class="bg-rzp-card border border-rzp-border rounded-xl p-5 flex flex-col justify-between hover:border-slate-700 transition">
                    <div>
                        <div class="flex items-center justify-between">
                            <span class="text-[10px] font-bold tracking-wider uppercase px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">PORT 8000</span>
                            <span id="health-b2b" class="text-[10px] font-bold text-rzp-green">ACTIVE</span>
                        </div>
                        <h3 class="text-base font-bold text-white mt-3">Bharat Connect B2B Switch</h3>
                        <p class="text-xs text-rzp-textMuted mt-1 leading-relaxed">
                            Automated GST calculation, double-entry tax isolation in paise, and autonomous POD dispute arbitration.
                        </p>
                    </div>
                    <div class="mt-6 pt-4 border-t border-rzp-border">
                        <button onclick="triggerEngine('/api/b2b/test', 'B2B Settlement')" class="w-full bg-rzp-blue hover:bg-rzp-blueHover text-white text-xs font-semibold py-2.5 px-4 rounded-lg shadow-sm transition flex items-center justify-center gap-2">
                            <i class="fa-solid fa-play text-[10px]"></i> Execute Split Settlement
                        </button>
                    </div>
                </div>
                <div id="upi-section" class="bg-rzp-card border border-rzp-border rounded-xl p-5 flex flex-col justify-between hover:border-slate-700 transition">
                    <div>
                        <div class="flex items-center justify-between">
                            <span class="text-[10px] font-bold tracking-wider uppercase px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">PORT 8001</span>
                            <span id="health-upi" class="text-[10px] font-bold text-rzp-green">ACTIVE</span>
                        </div>
                        <h3 class="text-base font-bold text-white mt-3">UPI Circle & Overdraft Switch</h3>
                        <p class="text-xs text-rzp-textMuted mt-1 leading-relaxed">
                            Role-based payment delegation, monthly spend limits, and automatic fallback drawdowns on linked pre-approved credit lines.
                        </p>
                    </div>
                    <div class="mt-6 pt-4 border-t border-rzp-border">
                        <button onclick="triggerEngine('/api/upi/test', 'UPI Delegation')" class="w-full bg-rzp-blue hover:bg-rzp-blueHover text-white text-xs font-semibold py-2.5 px-4 rounded-lg shadow-sm transition flex items-center justify-center gap-2">
                            <i class="fa-solid fa-play text-[10px]"></i> Trigger Circle Drawdown
                        </button>
                    </div>
                </div>
                <div id="risk-section" class="bg-rzp-card border border-rzp-border rounded-xl p-5 flex flex-col justify-between hover:border-slate-700 transition">
                    <div>
                        <div class="flex items-center justify-between">
                            <span class="text-[10px] font-bold tracking-wider uppercase px-2 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20">PORT 8002</span>
                            <span id="health-risk" class="text-[10px] font-bold text-rzp-green">ACTIVE</span>
                        </div>
                        <h3 class="text-base font-bold text-white mt-3">ULI & MuleHunter.AI Shield</h3>
                        <p class="text-xs text-rzp-textMuted mt-1 leading-relaxed">
                            Land registry agri-scoring engine coupled with directed graph velocity inspection to freeze money-mule accounts in real time.
                        </p>
                    </div>
                    <div class="mt-6 pt-4 border-t border-rzp-border">
                        <button onclick="triggerEngine('/api/risk/test', 'MuleHunter Audit')" class="w-full bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold py-2.5 px-4 rounded-lg shadow-sm transition flex items-center justify-center gap-2">
                            <i class="fa-solid fa-play text-[10px]"></i> Test ULI Sanction & Freeze
                        </button>
                    </div>
                </div>
            </div>
            <div class="bg-rzp-sidebar border border-rzp-border rounded-xl p-5 shadow-xl">
                <div class="flex items-center justify-between pb-3 border-b border-rzp-border">
                    <div class="flex items-center gap-2">
                        <span class="w-2 h-2 rounded-full bg-rzp-green"></span>
                        <span class="text-xs font-bold uppercase tracking-wider text-slate-300">Live Transaction Telemetry Stream</span>
                    </div>
                    <button onclick="clearLogs()" class="text-[11px] text-slate-500 hover:text-slate-300 font-medium">Clear Terminal</button>
                </div>
                <div id="terminal" class="terminal-font bg-black/60 rounded-lg p-4 mt-3 h-52 overflow-y-auto text-emerald-400 space-y-1.5 border border-slate-900">
                    <div>[GATEWAY] System initialized. Routing active on Port 8080. Ready for transactions...</div>
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
                    if(data.risk.mule_status === 'LIEN_FREEZE_PLACED') {
                        m.className = 'text-lg font-bold mt-1 font-mono text-rose-400';
                    }
                }
            } catch(e) {}
        }
        async function triggerEngine(endpoint, tag) {
            log(`>>> DISPATCHING ${tag} REQUEST -> ${endpoint}`);
            try {
                const res = await fetch(endpoint);
                const json = await res.json();
                log(`<<< RECEIVED RESPONSE [HTTP ${res.status}]:\n` + JSON.stringify(json, null, 2));
                pollAll();
            } catch (e) {
                log(`!!! ERROR: ${e.message}`);
            }
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
            document.getElementById('terminal').innerHTML = '<div>[TERMINAL RESET]</div>';
        }
        setInterval(pollAll, 4000);
        pollAll();
    </script>
</body>
</html>"""

@app.get("/api/state/metrics")
async def get_state():
    metrics = {"b2b": None, "upi": None, "risk": None}
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

@app.get("/api/b2b/test")
async def run_b2b():
    async with httpx.AsyncClient(timeout=5.0) as client:
        import uuid
        inv_id = f"INV-{uuid.uuid4().hex[:6].upper()}"
        await client.post(f"{SWITCHES['b2b']}/api/v1/invoices/present", json={
            "invoice_id": inv_id,
            "supplier_gstin": "27AABCU9603R1ZM",
            "buyer_gstin": "27AABCT1332L1ZV",
            "is_interstate": False,
            "line_items": [{"item_desc": "Enterprise Switch Blade", "hsn_code": "8537", "quantity": 1, "unit_price": 50000.0, "gst_rate_percent": 18.0}]
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
