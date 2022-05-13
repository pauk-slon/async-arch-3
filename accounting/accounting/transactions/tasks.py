from sqlalchemy import select

from accounting import database
from accounting.models import TaskAssignment, Task, Account, BillingCycle, BillingCycleStatus, Transaction
from accounting.transactions.utils import get_or_create


async def price_task(task_public_id: str) -> Task:
    async with database.create_session() as session:
        task, _created = await get_or_create(session, Task, public_id=task_public_id)
        task.price()
        await session.commit()
        await session.refresh(task)
        return task


async def charge_fee_for_task_assignment(task_public_id: str, account_public_id: str) -> TaskAssignment:
    async with database.create_session() as session:
        task, task_created = await get_or_create(session, Task, public_id=task_public_id)
        if task.is_not_priced:
            task.price()
        if task_created:
            await session.commit()
        account, account_created = await get_or_create(session, Account, public_id=account_public_id)
        if account_created:
            await session.commit()
            await session.refresh(account)
        billing_cycle, billing_cycle_created = (
            await get_or_create(session, BillingCycle, account_id=account.id, status=BillingCycleStatus.open)
        )
        if billing_cycle_created:
            await session.commit()
            await session.refresh(billing_cycle)
        current_billing_cycle: BillingCycle = (await session.execute(
            select(BillingCycle).where(
                BillingCycle.status == BillingCycleStatus.open,
                BillingCycle.account_id == account.id,
            ).with_for_update()
        )).scalar_one()
        transaction = Transaction(
            billing_cycle_id=current_billing_cycle.id,
            debit=0,
            credit=task.assignment_cost,
        )
        session.add(transaction)
        await session.flush()
        await session.refresh(transaction)
        task_assignment = TaskAssignment(transaction_id=transaction.id, task_id=task.id)
        session.add(task_assignment)
        await session.commit()
        await session.refresh(task_assignment)
        return task_assignment
