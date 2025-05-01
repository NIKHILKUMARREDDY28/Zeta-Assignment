import datetime
import traceback
from enum import Enum
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, condecimal, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.task3.db_connection import (
    get_session, get_account_with_lock, get_account,
    create_transaction
)
from app.task3.utils import rate_limiter


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


if __name__ == '__main__':
    import uvicorn
    import os
    import sys

    # Add the current directory to the Python path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(current_dir)

    # Run the FastAPI app
    uvicorn.run(app, host="0.0.0.0", port=8000)