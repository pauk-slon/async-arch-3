from contextlib import asynccontextmanager
import dataclasses
from typing import AsyncContextManager

from sqlalchemy import select

from accounting import database
from accounting.models import Account, BillingCycle, BillingCycleStatus, Transaction
from accounting.transactions.utils import get_or_create


async def initialize_account(account_public_id: str):
    async with database.create_session() as init_session:
        account, account_created = await get_or_create(init_session, Account, public_id=account_public_id)
        if account_created:
            await init_session.commit()
            await init_session.refresh(account)
        billing_cycle, billing_cycle_created = (
            await get_or_create(init_session, BillingCycle, account_id=account.id, status=BillingCycleStatus.open)
        )
        if billing_cycle_created:
            await init_session.commit()
            await init_session.refresh(billing_cycle)


@dataclasses.dataclass
class BillingTransactionContext:
    session: database.AsyncSession
    billing_cycle: BillingCycle

    async def create_transaction(self, debit: int, credit: int) -> Transaction:
        transaction = Transaction(
            billing_cycle_id=self.billing_cycle.id,
            debit=debit,
            credit=credit,
        )
        self.session.add(transaction)
        await self.session.flush([transaction])
        await self.session.refresh(transaction)
        return transaction


@asynccontextmanager
async def billing_transaction(account_public_id: str) -> AsyncContextManager[BillingTransactionContext]:
    async with database.create_session() as session:
        billing_cycle = (await session.execute(
            select(BillingCycle).join(Account).where(
                BillingCycle.status == BillingCycleStatus.open,
                Account.public_id == account_public_id,
            ).with_for_update()
        )).scalar_one()
        yield BillingTransactionContext(session, billing_cycle)
