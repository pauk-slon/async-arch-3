from contextlib import asynccontextmanager

from sqlalchemy import select

from accounting import database
from accounting.models import TaskAssignment, Task, TaskClosing
from accounting.transactions.billing import billing_transaction
from accounting.transactions.utils import get_or_create


async def price_task(task_public_id: str):
    async with database.create_session() as session:
        task, _created = await get_or_create(session, Task, public_id=task_public_id)
        task.price()
        await session.commit()


@asynccontextmanager
async def _task_billing_transaction(task_public_id: str, account_public_id: str):
    task_query = select(Task).where(Task.public_id == task_public_id)
    async with billing_transaction(account_public_id) as billing_context:
        task: Task = (await billing_context.session.execute(task_query)).scalar_one()
        yield task, billing_context


async def charge_fee_for_task_assignment(task_public_id: str, account_public_id: str):
    async with _task_billing_transaction(task_public_id, account_public_id) as (task, billing_context):
        transaction = await billing_context.create_transaction(debit=0, credit=task.assignment_cost)
        billing_context.session.add(TaskAssignment(transaction_id=transaction.id, task_id=task.id))
        await billing_context.session.commit()


async def assess_amount_for_task_closing(task_public_id, account_public_id):
    async with _task_billing_transaction(task_public_id, account_public_id) as (task, billing_context):
        transaction = await billing_context.create_transaction(debit=task.closing_cost, credit=0)
        billing_context.session.add(TaskClosing(transaction_id=transaction.id, task_id=task.id))
        await billing_context.session.commit()
