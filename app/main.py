import datetime
import traceback
from enum import Enum
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, condecimal, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.db_connection import (
    get_session, get_account_with_lock, get_account,
    create_transaction, Account
)
from app.utils import rate_limiter


class DebitRequest(BaseModel):
    account_id: int
    amount: condecimal(gt=0)

class CreditRequest(BaseModel):
    account_id: int
    amount: condecimal(gt=0)

class TransactionResponse(BaseModel):
    account_id: int
    new_balance: condecimal()
    message: str

class BalanceResponse(BaseModel):
    account_id: int
    balance: condecimal()
    currency: str

app = FastAPI()

@app.post("/transactions/debit", response_model=TransactionResponse)
@rate_limiter(limit=5, period=60)
async def debit_funds(
    req: DebitRequest,
    session: AsyncSession = Depends(get_session)
):
    try:
        async with session.begin():
            acct = await get_account_with_lock(session, req.account_id)

            if not acct:
                raise HTTPException(status_code=404, detail="Account not found")
            if acct.balance < req.amount:
                raise HTTPException(status_code=400, detail="Insufficient funds")

            # Perform the debit
            acct.balance -= req.amount

            # Record the transaction
            await create_transaction(
                session,
                req.account_id,
                "debit",
                req.amount
            )

        return TransactionResponse(
            account_id=req.account_id,
            new_balance=acct.balance,
            message="Debit successful"
        )

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        await session.rollback()
        print(f"Database error: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal database error")

@app.post("/transactions/credit", response_model=TransactionResponse)
async def credit_funds(
    req: CreditRequest,
    session: AsyncSession = Depends(get_session)
):
    try:
        async with session.begin():
            acct = await get_account_with_lock(session, req.account_id)

            if not acct:
                raise HTTPException(status_code=404, detail="Account not found")

            # Perform the credit
            acct.balance += req.amount

            # Record the transaction
            await create_transaction(
                session,
                req.account_id,
                "credit",
                req.amount
            )

        return TransactionResponse(
            account_id=req.account_id,
            new_balance=acct.balance,
            message="Credit successful"
        )

    except HTTPException:
        raise
    except SQLAlchemyError:
        await session.rollback()
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal database error")

@app.get("/accounts/{account_id}/balance", response_model=BalanceResponse)
async def get_balance(
    account_id: int,
    session: AsyncSession = Depends(get_session)
):
    try:
        acct = await get_account(session, account_id)

        if not acct:
            raise HTTPException(status_code=404, detail="Account not found")

        return BalanceResponse(
            account_id=acct.id,
            balance=acct.balance,
            currency=acct.currency
        )

    except HTTPException:
        raise
    except SQLAlchemyError:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal database error")


# Define enums for dispute categories and status
class DisputeCategory(str, Enum):
    PAYMENT = "payment"
    DELIVERY = "delivery"
    QUALITY = "quality"
    SERVICE = "service"
    OTHER = "other"

class DisputeStatus(str, Enum):
    PENDING = "pending"
    IN_REVIEW = "in_review"
    RESOLVED = "resolved"
    CLOSED = "closed"

class PriorityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class RecommendedAction(str, Enum):
    REFUND = "issue_refund"
    REPLACEMENT = "send_replacement"
    ADDITIONAL_INFO = "request_additional_info"
    ESCALATE = "escalate_to_manager"
    REJECT = "reject_dispute"

# Models
class DisputeRequest(BaseModel):
    customer_id: str
    order_id: str
    amount: float
    category: DisputeCategory
    description: str
    customer_history: Optional[dict] = Field(
        default=None,
        example={
            "total_orders": 15,
            "previous_disputes": 2,
            "account_age_days": 180
        }
    )

class DisputeResponse(BaseModel):
    dispute_id: str
    priority: PriorityLevel
    risk_level: float
    recommended_action: RecommendedAction
    status: DisputeStatus = DisputeStatus.PENDING
    created_at: datetime.datetime

# In-memory storage for disputes
disputes = {}

# Simple AI rule system for risk assessment
def assess_risk(dispute: DisputeRequest) -> float:
    """Calculate risk score based on simple rules"""
    risk_score = 0.0

    # Amount-based risk
    if dispute.amount > 1000:
        risk_score += 0.4
    elif dispute.amount > 500:
        risk_score += 0.2
    elif dispute.amount > 100:
        risk_score += 0.1

    # Category-based risk
    if dispute.category == DisputeCategory.PAYMENT:
        risk_score += 0.3
    elif dispute.category == DisputeCategory.QUALITY:
        risk_score += 0.2

    # Description-based risk (looking for keywords indicating fraud)
    fraud_keywords = ["never received", "not authorized", "fraud", "scam", "fake"]
    if any(keyword in dispute.description.lower() for keyword in fraud_keywords):
        risk_score += 0.3

    # Customer history based risk
    if dispute.customer_history:
        prev_disputes = dispute.customer_history.get("previous_disputes", 0)
        total_orders = max(dispute.customer_history.get("total_orders", 1), 1)
        account_age = dispute.customer_history.get("account_age_days", 365)

        # Higher ratio of disputes to orders indicates higher risk
        dispute_ratio = prev_disputes / total_orders
        if dispute_ratio > 0.2:
            risk_score += 0.3
        elif dispute_ratio > 0.1:
            risk_score += 0.1

        # New accounts have higher risk
        if account_age < 30:
            risk_score += 0.2
        elif account_age < 90:
            risk_score += 0.1

    # Cap the risk score at 1.0
    return min(risk_score, 1.0)

def determine_priority(risk_score: float) -> PriorityLevel:
    """Determine priority level based on risk score"""
    if risk_score > 0.7:
        return PriorityLevel.CRITICAL
    elif risk_score > 0.5:
        return PriorityLevel.HIGH
    elif risk_score > 0.3:
        return PriorityLevel.MEDIUM
    else:
        return PriorityLevel.LOW

def recommend_action(dispute: DisputeRequest, risk_score: float) -> RecommendedAction:
    """Recommend action based on dispute details and risk score"""
    if risk_score > 0.7:
        return RecommendedAction.ESCALATE

    if dispute.category == DisputeCategory.PAYMENT and risk_score > 0.5:
        return RecommendedAction.ADDITIONAL_INFO

    if dispute.category == DisputeCategory.DELIVERY:
        return RecommendedAction.REPLACEMENT

    if dispute.category == DisputeCategory.QUALITY:
        if dispute.amount < 100:
            return RecommendedAction.REFUND
        else:
            return RecommendedAction.ADDITIONAL_INFO

    if risk_score < 0.2:
        return RecommendedAction.REFUND

    return RecommendedAction.ADDITIONAL_INFO

@app.post("/disputes", response_model=DisputeResponse)
async def create_dispute(dispute: DisputeRequest):
    # Generate a simple dispute ID
    dispute_id = f"DISP-{len(disputes) + 1:04d}"

    # Assess risk using our rule system
    risk_score = assess_risk(dispute)

    # Determine priority based on risk
    priority = determine_priority(risk_score)

    # Recommend action
    action = recommend_action(dispute, risk_score)

    # Create response
    response = DisputeResponse(
        dispute_id=dispute_id,
        priority=priority,
        risk_level=round(risk_score, 2),
        recommended_action=action,
        created_at=datetime.datetime.now()
    )

    # Store the dispute
    disputes[dispute_id] = response

    return response

@app.get("/disputes/{dispute_id}", response_model=DisputeResponse)
async def get_dispute(dispute_id: str):
    if dispute_id not in disputes:
        raise HTTPException(status_code=404, detail="Dispute not found")
    return disputes[dispute_id]

if __name__ == '__main__':
    import uvicorn
    import os
    import sys

    # Add the current directory to the Python path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(current_dir)

    # Run the FastAPI app
    uvicorn.run(app, host="0.0.0.0", port=8000)