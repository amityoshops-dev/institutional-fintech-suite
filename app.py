from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
import enum
import json
import logging
from typing import List, Optional
import uuid

from fastapi import Depends, FastAPI, Header, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BharatConnectSwitch")

DATABASE_URL = "sqlite:///./bharat_connect_b2b.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def current_utc():
    return datetime.now(timezone.utc)


# ---------------------------------------------------------
# ENUMS & MODELS
# ---------------------------------------------------------
class InvoiceStatus(str, enum.Enum):
    PRESENTED = "PRESENTED"
    APPROVED = "APPROVED"
    SETTLED = "SETTLED"
    DISPUTED = "DISPUTED"


class AccountType(str, enum.Enum):
    ASSET = "ASSET"
    LIABILITY = "LIABILITY"
    ESCROW = "ESCROW"


class EntryType(str, enum.Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"


class DisputeStatus(str, enum.Enum):
    OPEN = "OPEN"
    AUTO_RESOLVED = "AUTO_RESOLVED"
    LIEN_PLACED = "LIEN_PLACED"


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_keys"
    key = Column(String(128), primary_key=True, index=True)
    response_code = Column(BigInteger, nullable=False)
    response_body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=current_utc, nullable=False)


class Account(Base):
    __tablename__ = "accounts"
    account_id = Column(String(64), primary_key=True)
    name = Column(String(128), nullable=False)
    account_type = Column(SQLEnum(AccountType), nullable=False)
    balance_paise = Column(BigInteger, default=0, nullable=False)


class JournalEntry(Base):
    __tablename__ = "journal_entries"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    reference_id = Column(String(128), nullable=False, index=True)
    narration = Column(String(256), nullable=False)
    created_at = Column(DateTime, default=current_utc, nullable=False)
    postings = relationship(
        "LedgerPosting", back_populates="journal", cascade="all, delete-orphan"
    )


class LedgerPosting(Base):
    __tablename__ = "ledger_postings"
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    journal_id = Column(
        String(64), ForeignKey("journal_entries.id"), nullable=False
    )
    account_id = Column(String(64), ForeignKey("accounts.account_id"), nullable=False)
    entry_type = Column(SQLEnum(EntryType), nullable=False)
    amount_paise = Column(BigInteger, nullable=False)
    journal = relationship("JournalEntry", back_populates="postings")


class Invoice(Base):
    __tablename__ = "invoices"
    invoice_id = Column(String(64), primary_key=True, index=True)
    supplier_gstin = Column(String(15), nullable=False)
    buyer_gstin = Column(String(15), nullable=False)
    base_amount_paise = Column(BigInteger, nullable=False)
    cgst_paise = Column(BigInteger, default=0, nullable=False)
    sgst_paise = Column(BigInteger, default=0, nullable=False)
    igst_paise = Column(BigInteger, default=0, nullable=False)
    total_amount_paise = Column(BigInteger, nullable=False)
    status = Column(
        SQLEnum(InvoiceStatus), default=InvoiceStatus.PRESENTED, nullable=False
    )
    utr = Column(String(64), nullable=True)
    lien_placed = Column(BigInteger, default=0, nullable=False)
    created_at = Column(DateTime, default=current_utc, nullable=False)


class Dispute(Base):
    __tablename__ = "disputes"
    dispute_id = Column(
        String(64),
        primary_key=True,
        default=lambda: f"DSP-{uuid.uuid4().hex[:8].upper()}",
    )
    invoice_id = Column(
        String(64), ForeignKey("invoices.invoice_id"), nullable=False
    )
    reason = Column(String(256), nullable=False)
    pod_reference = Column(String(128), nullable=True)
    status = Column(
        SQLEnum(DisputeStatus), default=DisputeStatus.OPEN, nullable=False
    )
    verdict_notes = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=current_utc, nullable=False)


Base.metadata.create_all(bind=engine)

# ---------------------------------------------------------
# PYDANTIC SCHEMAS
# ---------------------------------------------------------
GSTIN_REGEX = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"


class LineItem(BaseModel):
    item_desc: str
    hsn_code: str
    quantity: int = Field(gt=0)
    unit_price: Decimal = Field(gt=0)
    gst_rate_percent: Decimal = Field(ge=0, le=28)


class InvoicePresentmentRequest(BaseModel):
    invoice_id: str
    supplier_gstin: str = Field(pattern=GSTIN_REGEX)
    buyer_gstin: str = Field(pattern=GSTIN_REGEX)
    line_items: List[LineItem]
    is_interstate: bool = False


class SettleInvoiceRequest(BaseModel):
    buyer_virtual_account: str
    force_immediate: bool = False


class DisputeRequest(BaseModel):
    reason: str
    shipping_awb_tracking_no: str


# ---------------------------------------------------------
# FASTAPI APPLICATION
# ---------------------------------------------------------
app = FastAPI(title="Bharat Connect B2B Settlement Engine", version="2.3.0")


def seed_accounts(db: Session):
    core_accounts = [
        ("ACC-BUYER-CLEARING", "Buyer Inbound Clearing", AccountType.LIABILITY),
        ("ACC-GST-ESCROW", "Central Tax Escrow Holding", AccountType.ESCROW),
        (
            "ACC-SUPPLIER-PAYABLE",
            "Vendor Settlement Payout Node",
            AccountType.LIABILITY,
        ),
    ]
    for acc_id, name, acc_type in core_accounts:
        existing = (
            db.query(Account).filter(Account.account_id == acc_id).first()
        )
        if not existing:
            db.add(
                Account(
                    account_id=acc_id,
                    name=name,
                    account_type=acc_type,
                    balance_paise=0,
                )
            )
    db.commit()


@app.on_event("startup")
def startup_seed():
    db = SessionLocal()
    try:
        seed_accounts(db)
    finally:
        db.close()


@app.get("/api/v1/ledger/accounts")
def get_ledger_balances(db: Session = Depends(get_db)):
    accounts = db.query(Account).all()
    return [
        {
            "account_id": a.account_id,
            "name": a.name,
            "type": a.account_type.value,
            "balance_inr": f"{a.balance_paise / 100:.2f}",
        }
        for a in accounts
    ]


@app.post("/api/v1/invoices/present", status_code=status.HTTP_201_CREATED)
def present_invoice(
    payload: InvoicePresentmentRequest,
    x_idempotency_key: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    try:
        if x_idempotency_key:
            cached = (
                db.query(IdempotencyRecord)
                .filter(IdempotencyRecord.key == x_idempotency_key)
                .first()
            )
            if cached:
                return Response(
                    content=cached.response_body,
                    status_code=int(cached.response_code),
                    media_type="application/json",
                )

        existing = (
            db.query(Invoice)
            .filter(Invoice.invoice_id == payload.invoice_id)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Invoice ID '{payload.invoice_id}' already registered.",
            )

        total_base = Decimal("0.00")
        total_tax = Decimal("0.00")
        for item in payload.line_items:
            line_base = item.quantity * item.unit_price
            line_tax = line_base * (item.gst_rate_percent / Decimal("100"))
            total_base += line_base
            total_tax += line_tax

        base_paise = int(
            (total_base * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        )
        tax_paise = int(
            (total_tax * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        )

        if payload.is_interstate:
            igst_paise = tax_paise
            cgst_paise = 0
            sgst_paise = 0
        else:
            igst_paise = 0
            cgst_paise = tax_paise // 2
            sgst_paise = tax_paise - cgst_paise

        total_amount_paise = base_paise + tax_paise

        invoice = Invoice(
            invoice_id=payload.invoice_id,
            supplier_gstin=payload.supplier_gstin,
            buyer_gstin=payload.buyer_gstin,
            base_amount_paise=base_paise,
            cgst_paise=cgst_paise,
            sgst_paise=sgst_paise,
            igst_paise=igst_paise,
            total_amount_paise=total_amount_paise,
            status=InvoiceStatus.PRESENTED,
        )
        db.add(invoice)
        db.commit()

        resp = {
            "status": "SUCCESS",
            "invoice_id": invoice.invoice_id,
            "financial_summary": {
                "base_inr": f"{base_paise / 100:.2f}",
                "cgst_inr": f"{cgst_paise / 100:.2f}",
                "sgst_inr": f"{sgst_paise / 100:.2f}",
                "igst_inr": f"{igst_paise / 100:.2f}",
                "total_payable_inr": f"{total_amount_paise / 100:.2f}",
            },
            "network_state": invoice.status.value,
        }

        if x_idempotency_key:
            db.add(
                IdempotencyRecord(
                    key=x_idempotency_key,
                    response_code=201,
                    response_body=json.dumps(resp),
                )
            )
            db.commit()

        return resp
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in present_invoice: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Presentment failed: {str(e)}")


@app.post("/api/v1/invoices/{invoice_id}/dispute")
def raise_dispute(
    invoice_id: str, payload: DisputeRequest, db: Session = Depends(get_db)
):
    try:
        invoice = (
            db.query(Invoice).filter(Invoice.invoice_id == invoice_id).first()
        )
        if not invoice:
            raise HTTPException(
                status_code=404,
                detail=f"Invoice '{invoice_id}' not found in database.",
            )

        dispute = Dispute(
            invoice_id=invoice_id,
            reason=payload.reason,
            pod_reference=payload.shipping_awb_tracking_no,
            status=DisputeStatus.OPEN,
        )
        db.add(dispute)
        invoice.status = InvoiceStatus.DISPUTED

        tracking = payload.shipping_awb_tracking_no.upper()
        if "POD" in tracking or "DELIVERED" in tracking:
            dispute.status = DisputeStatus.AUTO_RESOLVED
            dispute.verdict_notes = (
                "Proof of Delivery confirmed. Dispute dismissed; invoice"
                " approved."
            )
            invoice.status = InvoiceStatus.APPROVED
            invoice.lien_placed = 0
        else:
            dispute.status = DisputeStatus.LIEN_PLACED
            dispute.verdict_notes = (
                "Courier telemetry in-transit. Lien placed on payout."
            )
            invoice.status = InvoiceStatus.DISPUTED
            invoice.lien_placed = invoice.base_amount_paise

        db.commit()
        return {
            "status": "DISPUTE_EVALUATED",
            "dispute_id": dispute.dispute_id,
            "dispute_status": dispute.status.value,
            "invoice_status": invoice.status.value,
            "verdict": dispute.verdict_notes,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in raise_dispute: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Dispute failed: {str(e)}")


@app.post("/api/v1/invoices/{invoice_id}/settle")
def settle_invoice(
    invoice_id: str,
    payload: SettleInvoiceRequest,
    db: Session = Depends(get_db),
):
    try:
        invoice = (
            db.query(Invoice).filter(Invoice.invoice_id == invoice_id).first()
        )
        if not invoice:
            raise HTTPException(
                status_code=404,
                detail=f"Invoice '{invoice_id}' not found in database.",
            )

        if invoice.status == InvoiceStatus.SETTLED:
            raise HTTPException(
                status_code=400, detail="Invoice is already settled."
            )

        if (
            invoice.status == InvoiceStatus.DISPUTED
            and not payload.force_immediate
        ):
            raise HTTPException(
                status_code=412,
                detail="Invoice holds active dispute. Lien blocks settlement.",
            )

        tax_total_paise = (
            invoice.cgst_paise + invoice.sgst_paise + invoice.igst_paise
        )
        net_supplier_payout_paise = invoice.base_amount_paise

        journal = JournalEntry(
            reference_id=invoice.invoice_id,
            narration=f"B2B Split Settlement for {invoice.invoice_id}",
        )
        db.add(journal)
        db.flush()

        postings = [
            LedgerPosting(
                journal_id=journal.id,
                account_id="ACC-BUYER-CLEARING",
                entry_type=EntryType.DEBIT,
                amount_paise=invoice.total_amount_paise,
            ),
            LedgerPosting(
                journal_id=journal.id,
                account_id="ACC-GST-ESCROW",
                entry_type=EntryType.CREDIT,
                amount_paise=tax_total_paise,
            ),
            LedgerPosting(
                journal_id=journal.id,
                account_id="ACC-SUPPLIER-PAYABLE",
                entry_type=EntryType.CREDIT,
                amount_paise=net_supplier_payout_paise,
            ),
        ]
        db.add_all(postings)

        buyer_acc = (
            db.query(Account)
            .filter(Account.account_id == "ACC-BUYER-CLEARING")
            .first()
        )
        tax_escrow = (
            db.query(Account)
            .filter(Account.account_id == "ACC-GST-ESCROW")
            .first()
        )
        supplier_node = (
            db.query(Account)
            .filter(Account.account_id == "ACC-SUPPLIER-PAYABLE")
            .first()
        )

        buyer_acc.balance_paise += invoice.total_amount_paise
        tax_escrow.balance_paise += tax_total_paise
        supplier_node.balance_paise += net_supplier_payout_paise

        utr = f"UTR-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
        invoice.utr = utr
        invoice.status = InvoiceStatus.SETTLED
        db.commit()

        return {
            "status": "SETTLED",
            "utr": utr,
            "split_allocation": {
                "tax_escrow_inr": f"{tax_total_paise / 100:.2f}",
                "supplier_net_inr": f"{net_supplier_payout_paise / 100:.2f}",
                "total_cleared_inr": f"{invoice.total_amount_paise / 100:.2f}",
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in settle_invoice: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Settle failed: {str(e)}")