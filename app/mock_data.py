import asyncio
import random
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.db_connection import DATABASE_URL, Account, Transaction, Base


engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

# Sample data
CURRENCIES = ["USD", "EUR", "GBP", "JPY", "CNY"]
TRANSACTION_TYPES = ["debit", "credit"]


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


async def insert_mock_data():
    async with AsyncSessionLocal() as session:
        async with session.begin():
            # Create 10 accounts with random balances
            accounts = []
            for i in range(1, 11):
                initial_balance = Decimal(str(random.uniform(1000, 10000))).quantize(Decimal("0.01"))
                currency = random.choice(CURRENCIES)
                account = Account(
                    balance=initial_balance,
                    currency=currency
                )
                session.add(account)
                accounts.append(account)

            await session.flush()  # Flush to get IDs

            # Create transactions for each account
            for account in accounts:
                # Generate between 5-15 transactions per account
                num_transactions = random.randint(5, 15)

                for _ in range(num_transactions):
                    txn_type = random.choice(TRANSACTION_TYPES)
                    amount = Decimal(str(random.uniform(10, 500))).quantize(Decimal("0.01"))

                    # Create random timestamp within last 30 days
                    days_ago = random.randint(0, 30)
                    hours_ago = random.randint(0, 23)
                    minutes_ago = random.randint(0, 59)
                    created_at = datetime.now() - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)

                    transaction = Transaction(
                        account_id=account.id,
                        type=txn_type,
                        amount=amount,
                        created_at=created_at
                    )
                    session.add(transaction)

            print(f"Created {len(accounts)} accounts and approximately {len(accounts) * 10} transactions")


async def main():
    await create_tables()
    await insert_mock_data()


if __name__ == "__main__":
    asyncio.run(main())