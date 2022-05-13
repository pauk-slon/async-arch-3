from sqlalchemy import select

from accounting import database
from accounting.models import TaskAssignment, Task, TaskClosing, Transaction
from accounting.transactions.billing import get_current_billing_cycle
from accounting.transactions.utils import get_or_create


async def price_task(task_public_id: str) -> int:
    async with database.create_session() as session:
        task, _created = await get_or_create(session, Task, public_id=task_public_id)
        task.price()
        await session.commit()


async def charge_fee_for_task_assignment(task_public_id: str, account_public_id: str) -> TaskAssignment:
    async with database.create_session() as session:
        task = (await session.execute(select(Task).where(Task.public_id == task_public_id))).scalar_one()
        billing_cycle = await get_current_billing_cycle(session, account_public_id)
        transaction = Transaction(billing_cycle_id=billing_cycle.id, debit=0, credit=task.assignment_cost)
        session.add(transaction)
        await session.flush()
        await session.refresh(transaction)
        task_assignment = TaskAssignment(transaction_id=transaction.id, task_id=task.id)
        session.add(task_assignment)
        await session.commit()
        await session.refresh(task_assignment)
        return task_assignment


async def assess_amount_for_task_completion(task_public_id, account_public_id) -> TaskClosing:
    async with database.create_session() as session:
        task: Task = (await session.execute(select(Task).where(Task.public_id == task_public_id))).scalar_one()
        billing_cycle = await get_current_billing_cycle(session, account_public_id)
        transaction = Transaction(billing_cycle_id=billing_cycle.id, debit=task.closing_cost, credit=0)
        session.add(transaction)
        await session.flush()
        await session.refresh(transaction)
        task_closing = TaskClosing(transaction_id=transaction.id, task_id=task.id)
        session.add(task_closing)
        await session.commit()
        await session.refresh(task_closing)
        return task_closing
