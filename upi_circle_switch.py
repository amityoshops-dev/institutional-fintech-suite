import uuid, enum, logging
from typing import Dict
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO)

class DelegationMode(str, enum.Enum):
    FULL = "FULL"
    PARTIAL = "PARTIAL"

class TxnStatus(str, enum.Enum):
    PENDING_PRIMARY_APPROVAL = "PENDING_PRIMARY_APPROVAL"
    APPROVED_AND_SETTLED = "APPROVED_AND_SETTLED"

class FundingSource(str, enum.Enum):
    SAVINGS_ACCOUNT = "SAVINGS_ACCOUNT"
    HYBRID_SPLIT = "HYBRID_SPLIT"

ACCOUNTS_DB: Dict[str, dict] = {}
CIRCLES_DB: Dict[str, dict] = {}
TXN_DB: Dict[str, dict] = {}

def seed_data():
    ACCOUNTS_DB["parent@bank"] = {
        "user_id": "USR-PARENT-01", "upi_id": "parent@bank", "pin": "1234",
        "savings_paise": 200000, "credit_line_paise": 5000000, "credit_drawn_paise": 0
    }
    ACCOUNTS_DB["kid@bank"] = {
        "user_id": "USR-KID-01", "upi_id": "kid@bank", "pin": "0000",
        "savings_paise": 0, "credit_line_paise": 0, "credit_drawn_paise": 0
    }

@asynccontextmanager
async def lifespan(app: FastAPI):
    seed_data()
    yield

app = FastAPI(title="UPI Circle Switch", lifespan=lifespan)

class AddSecondaryMemberRequest(BaseModel):
    primary_upi_id: str
    secondary_upi_id: str
    delegation_mode: DelegationMode
    monthly_limit_inr: float = Field(gt=0, le=15000)

class InitiatePaymentRequest(BaseModel):
    initiator_upi_id: str
    merchant_vpa: str
    amount_inr: float = Field(gt=0)

def execute_drawdown(primary_acc: dict, amount_paise: int) -> dict:
    savings = primary_acc["savings_paise"]
    available_credit = primary_acc["credit_line_paise"] - primary_acc["credit_drawn_paise"]
    if (savings + available_credit) < amount_paise:
        raise HTTPException(status_code=400, detail="Insufficient funds across savings & credit line.")
    if savings >= amount_paise:
        primary_acc["savings_paise"] -= amount_paise
        return {"source": FundingSource.SAVINGS_ACCOUNT.value, "debited_savings_inr": f"{amount_paise / 100:.2f}", "drawn_credit_line_inr": "0.00"}
    else:
        rem = amount_paise - savings
        primary_acc["savings_paise"] = 0
        primary_acc["credit_drawn_paise"] += rem
        return {"source": FundingSource.HYBRID_SPLIT.value, "debited_savings_inr": f"{savings / 100:.2f}", "drawn_credit_line_inr": f"{rem / 100:.2f}"}

@app.get("/api/v1/accounts/{upi_id}")
def get_account_status(upi_id: str):
    acc = ACCOUNTS_DB.get(upi_id)
    if not acc: raise HTTPException(status_code=404, detail="Account not found.")
    return {
        "upi_id": acc["upi_id"],
        "savings_balance_inr": f"{acc['savings_paise'] / 100:.2f}",
        "credit_line_available_inr": f"{(acc['credit_line_paise'] - acc['credit_drawn_paise']) / 100:.2f}",
        "total_credit_drawn_inr": f"{acc['credit_drawn_paise'] / 100:.2f}"
    }

@app.post("/api/v1/circle/link", status_code=status.HTTP_201_CREATED)
def link_secondary(payload: AddSecondaryMemberRequest):
    cid = f"CIRC-{uuid.uuid4().hex[:6].upper()}"
    CIRCLES_DB[payload.secondary_upi_id] = {
        "circle_id": cid, "primary_upi_id": payload.primary_upi_id,
        "mode": payload.delegation_mode, "limit_paise": int(payload.monthly_limit_inr * 100),
        "spent_this_month_paise": 0
    }
    return {"status": "LINKED", "circle_id": cid}

@app.post("/api/v1/payments/initiate")
def initiate_payment(payload: InitiatePaymentRequest):
    req_paise = int(payload.amount_inr * 100)
    circle = CIRCLES_DB.get(payload.initiator_upi_id)
    if circle and circle["mode"] == DelegationMode.FULL:
        primary_acc = ACCOUNTS_DB[circle["primary_upi_id"]]
        split_res = execute_drawdown(primary_acc, req_paise)
        circle["spent_this_month_paise"] += req_paise
        return {"status": "APPROVED_AND_SETTLED", "funding": split_res}
    raise HTTPException(status_code=400, detail="Invalid routing.")

@app.get("/api/v1/circle/test/run-all")
def run_all():
    seed_data()
    link_secondary(AddSecondaryMemberRequest(primary_upi_id="parent@bank", secondary_upi_id="kid@bank", delegation_mode=DelegationMode.FULL, monthly_limit_inr=5000.0))
    pay_res = initiate_payment(InitiatePaymentRequest(initiator_upi_id="kid@bank", merchant_vpa="store@upi", amount_inr=3500.0))
    acc_res = get_account_status("parent@bank")
    return {"status": "SUCCESS", "step_2_hybrid_payment": pay_res, "step_3_account_aftermath": acc_res}
