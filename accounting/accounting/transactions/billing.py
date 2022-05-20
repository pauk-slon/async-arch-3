from contextlib import asynccontextmanager
import dataclasses
from typing import AsyncContextManager, Iterable

from sqlalchemy import select

from accounting import database
from accounting.models import Account, BillingCycle, BillingCycleStatus, BillingTransaction, Payment
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
    account: Account
    billing_cycle: BillingCycle

    async def create_transaction(self, debit: int, credit: int) -> BillingTransaction:
        transaction = BillingTransaction(
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
        billing_cycle, account = (await session.execute(
            select(
                BillingCycle,
                Account,
            ).join(Account).where(
                BillingCycle.status == BillingCycleStatus.open,
                Account.public_id == account_public_id,
            ).with_for_update()
        )).one()
        yield BillingTransactionContext(session, account, billing_cycle)


async def close_current_billing_cycle(account_public_id: str):
    async with billing_transaction(account_public_id) as billing_context:
        billing_context.billing_cycle.close()
        billing_context.session.add(BillingCycle(account_id=billing_context.account.id))
        billing_cycle_transactions: Iterable[BillingTransaction] = (
            await billing_context.session.execute(
                select(BillingTransaction).where(
                    BillingTransaction.billing_cycle_id == billing_context.billing_cycle.id,
                )
            )
        ).scalars().all()
        debit, credit = 0, 0
        for billing_cycle_transaction in billing_cycle_transactions:
            debit += billing_cycle_transaction.debit
            credit += billing_cycle_transaction.credit
        billing_cycle_delta = debit - credit
        billing_context.account.balance += billing_cycle_delta
        if billing_context.account.balance > 0:
            payment_transaction = await billing_context.create_transaction(0, billing_context.account.balance)
            billing_context.session.add(Payment(billing_transaction_id=payment_transaction.id))
            billing_context.account.balance = 0
        await billing_context.session.commit()
