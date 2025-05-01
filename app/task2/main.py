from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import uvicorn

app = FastAPI()


BALANCES = { "cust_1": 1234.56 }
DISPUTES = []

class BalanceResponse(BaseModel):
    customer_id: str
    balance: float

class LoanRequest(BaseModel):
    customer_id: str
    credit_score: int
    monthly_income: float
    open_loans: int

class LoanResponse(BaseModel):
    eligibility_score: float
    recommendation: str

class Dispute(BaseModel):
    id: int
    customer_id: str
    issue: str
    status: str

class NewDispute(BaseModel):
    customer_id: str
    issue: str

def compute_eligibility(data: LoanRequest) -> LoanResponse:

    base = data.credit_score / 10
    income_pts = data.monthly_income / 1000
    loan_penalty = 2 * data.open_loans
    score = max(0, min(100, base + income_pts - loan_penalty))
    score = round(score, 1)

    if score >= 75:
        rec = f"You’re highly likely to be approved. You could request up to ${int(data.monthly_income * 5)}."
    elif score >= 50:
        rec = "Moderate eligibility. Consider lowering your amount or improving your credit score first."
    else:
        rec = "Low eligibility—focus on reducing debt and improving credit history before applying."

    return LoanResponse(eligibility_score=score, recommendation=rec)

@app.get("/balance", response_model=BalanceResponse)
def get_balance(customer_id: str):
    bal = BALANCES.get(customer_id)
    if bal is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return BalanceResponse(customer_id=customer_id, balance=bal)

@app.post("/loan-eligibility", response_model=LoanResponse)
def loan_eligibility(req: LoanRequest):
    return compute_eligibility(req)

@app.get("/disputes", response_model=List[Dispute])
def list_disputes(customer_id: str):
    return [d for d in DISPUTES if d["customer_id"] == customer_id]

@app.post("/disputes", response_model=Dispute)
def create_dispute(new: NewDispute):
    new_id = len(DISPUTES) + 1
    disc = {"id": new_id, "customer_id": new.customer_id, "issue": new.issue, "status": "Open"}
    DISPUTES.append(disc)
    return disc

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000)
