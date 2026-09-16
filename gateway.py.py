from fastapi import Request
from integrations import BankPayoutSandboxConnector, ERPReconciliationConnector

@app.post("/api/v1/erp/webhook/inbound")
async def receive_external_erp_invoice(request: Request):
    """
    Ingests live JSON payloads pushed directly from Zoho Books, ERPNext, or Postman.
    """
    body = await request.json()
    
    # 1. Normalize ERP Line Items
    inv_id = body.get("invoice_number", f"INV-{uuid.uuid4().hex[:6].upper()}")
    amount = float(body.get("total_amount", 59000.0))
    supplier_gst = body.get("supplier_gstin", "27AABCU9603R1ZM")
    buyer_gst = body.get("buyer_gstin", "27AABCT1332L1ZV")

    # 2. Forward to Port 8000 (Bharat Connect Split Engine)
    async with httpx.AsyncClient(timeout=5.0) as client:
        b2b_res = await client.post(f"{SWITCHES['b2b']}/api/v1/invoices/present", json={
            "invoice_id": inv_id,
            "supplier_gstin": supplier_gst,
            "buyer_gstin": buyer_gst,
            "is_interstate": False,
            "line_items": [
                {
                    "item_desc": "ERP Ingested Goods",
                    "hsn_code": "8471",
                    "quantity": 1,
                    "unit_price": amount / 1.18,
                    "gst_rate_percent": 18.0
                }
            ]
        })
        
        # 3. Trigger Bank Payout Sandbox (Cashfree/RazorpayX)
        payout_res = await BankPayoutSandboxConnector.create_virtual_account_payout(
            payee_vpa="supplier@bank",
            amount_inr=round(amount / 1.18, 2),
            transfer_id=f"TXN-{inv_id}"
        )
        
        # 4. Settle Switch Ledger with the Bank UTR
        settle_res = await client.post(f"{SWITCHES['b2b']}/api/v1/invoices/{inv_id}/settle", json={
            "buyer_virtual_account": "VA-ERP-BUYER",
            "force_immediate": True
        })

    return {
        "status": "ERP_PROCESSED_AND_SETTLED",
        "invoice_id": inv_id,
        "split_ledger": settle_res.json(),
        "sandbox_bank_response": payout_res
    }