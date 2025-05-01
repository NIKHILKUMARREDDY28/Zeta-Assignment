from sqlalchemy import (
    Column, Integer, Numeric, String,
    DateTime, ForeignKey, func, select
)
from sqlalchemy.ext.asyncio import (
    create_async_engine, AsyncSession, async_sessionmaker
)
from sqlalchemy.orm import declarative_base

DATABASE_URL = "postgresql+asyncpg://postgres:admin@localhost:5432/zeta-assignment"

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

Base = declarative_base()

class Account(Base):
    __tablename__ = "accounts"
    id         = Column(Integer, primary_key=True)
    balance    = Column(Numeric(14, 2), nullable=False, default=0)
    currency   = Column(String(3), nullable=False, default="USD")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True),
                        onupdate=func.now(),
                        server_default=func.now())

class Transaction(Base):
    __tablename__ = "transactions"
    id         = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    type       = Column(String(10), nullable=False)
    amount     = Column(Numeric(14, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


# Database operations
async def get_account_with_lock(session: AsyncSession, account_id: int):
    stmt = (
        select(Account)
        .where(Account.id == account_id)
        .with_for_update()
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

async def get_account(session: AsyncSession, account_id: int):
    stmt = select(Account).where(Account.id == account_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

async def create_transaction(session: AsyncSession, account_id: int,
                            transaction_type: str, amount: Numeric):
    txn = Transaction(
        account_id=account_id,
        type=transaction_type,
        amount=amount
    )
    session.add(txn)
    return txn