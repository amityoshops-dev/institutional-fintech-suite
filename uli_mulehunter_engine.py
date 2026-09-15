import uuid, enum, logging
from typing import Dict
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
import networkx as nx
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO)

class AccountRiskStatus(str, enum.Enum):
    HEALTHY = "HEALTHY"
    LIEN_FREEZE_PLACED = "LIEN_FREEZE_PLACED"

class CropType(str, enum.Enum):
    COTTON = "COTTON"

BANK_ACCOUNTS: Dict[str, dict] = {}
TRANSACTION_GRAPH = nx.DiGraph()

def seed_risk():
    for acc in ["ACC-ORIGIN-SHELL", "ACC-MULE-NODE-01", "ACC-EXIT-CASH-A", "ACC-EXIT-CASH-B"]:
        BANK_ACCOUNTS[acc] = {"account_id": acc, "balance_paise": 10000000, "status": AccountRiskStatus.HEALTHY.value}
        TRANSACTION_GRAPH.add_node(acc)

@asynccontextmanager
async def lifespan(app: FastAPI):
    seed_risk()
    yield

app = FastAPI(title="ULI & MuleHunter Switch", lifespan=lifespan)

class ULILoanApplicationRequest(BaseModel):
    farmer_aadhaar_hash: str
    state_land_khasra_no: str
    land_area_acres: float = Field(gt=0)
    crop_type: CropType
    account_aggregator_avg_inflow_inr: float = Field(ge=0)

class TransferTxnRequest(BaseModel):
    source_account: str
    destination_account: str
    amount_inr: float = Field(gt=0)

@app.post("/api/v1/uli/credit/evaluate", status_code=status.HTTP_201_CREATED)
def evaluate_uli(payload: ULILoanApplicationRequest):
    sanctioned = payload.land_area_acres * 55000
    return {"loan_application_id": f"ULI-{uuid.uuid4().hex[:6].upper()}", "status": "APPROVED", "sanctioned_credit_limit_inr": sanctioned}

@app.post("/api/v1/mulehunter/transfer")
def transfer(payload: TransferTxnRequest):
    src, dst = payload.source_account, payload.destination_account
    src_acc, dst_acc = BANK_ACCOUNTS[src], BANK_ACCOUNTS[dst]
    if src_acc["status"] == AccountRiskStatus.LIEN_FREEZE_PLACED.value:
        raise HTTPException(status_code=403, detail="Transfer blocked: Account has an active Lien Freeze.")
    src_acc["balance_paise"] -= int(payload.amount_inr * 100)
    dst_acc["balance_paise"] += int(payload.amount_inr * 100)
    TRANSACTION_GRAPH.add_edge(src, dst)
    if TRANSACTION_GRAPH.out_degree(src) >= 2:
        src_acc["status"] = AccountRiskStatus.LIEN_FREEZE_PLACED.value
    return {"status": "SETTLED", "source_risk_status": src_acc["status"]}

@app.get("/api/v1/mulehunter/network-status")
def net_status():
    return {"total_nodes": TRANSACTION_GRAPH.number_of_nodes(), "accounts": BANK_ACCOUNTS}

@app.get("/api/v1/system/test/run-all")
def run_all():
    seed_risk()
    u_res = evaluate_uli(ULILoanApplicationRequest(farmer_aadhaar_hash="HASH-123", state_land_khasra_no="K-1", land_area_acres=3.5, crop_type=CropType.COTTON, account_aggregator_avg_inflow_inr=30000.0))
    transfer(TransferTxnRequest(source_account="ACC-ORIGIN-SHELL", destination_account="ACC-MULE-NODE-01", amount_inr=20000.0))
    transfer(TransferTxnRequest(source_account="ACC-MULE-NODE-01", destination_account="ACC-EXIT-CASH-A", amount_inr=9000.0))
    transfer(TransferTxnRequest(source_account="ACC-MULE-NODE-01", destination_account="ACC-EXIT-CASH-B", amount_inr=9000.0))
    blocked = False
    try:
        transfer(TransferTxnRequest(source_account="ACC-MULE-NODE-01", destination_account="ACC-EXIT-CASH-A", amount_inr=1000.0))
    except HTTPException:
        blocked = True
    return {"status": "SUCCESS", "uli_sanction": u_res, "subsequent_transactions_blocked": blocked}
