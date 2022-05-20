from contextlib import asynccontextmanager
from typing import AsyncContextManager, Tuple

from sqlalchemy import select

from accounting import database
from accounting.event_producing import (
    emit_task_price_created_v1,
    emit_task_transaction_completed_v1,
)
from accounting.models import TaskAssignment, Task, TaskClosing, BillingTransaction
from accounting.transactions.billing import billing_transaction, BillingTransactionContext
from accounting.transactions.utils import get_or_create


async def price_task(task_public_id: str):
    async with database.create_session() as session:
        task, is_task_created = await get_or_create(session, Task, public_id=task_public_id)
        is_task_price_created = None
        if task.is_not_priced:
            task.price()
            is_task_price_created = True
        if is_task_created or is_task_price_created:
            await session.commit()
    if is_task_price_created:
        await emit_task_price_created_v1(task)


@asynccontextmanager
async def _task_billing_transaction(
        task_public_id: str,
        account_public_id: str,
) -> AsyncContextManager[Tuple[Task, BillingTransactionContext]]:
    task_query = select(Task).where(Task.public_id == task_public_id)
    async with billing_transaction(account_public_id) as billing_context:
        task: Task = (await billing_context.session.execute(task_query)).scalar_one()
        yield task, billing_context


async def _emit_event_task_transaction_completed(
        billing_context: BillingTransactionContext,
        transaction: BillingTransaction,
        transaction_type: str,
        task: Task
):
    await emit_task_transaction_completed_v1(
        billing_context.account,
        billing_context.billing_cycle.business_day,
        transaction,
        {'type': transaction_type, 'task': task.public_id },
    )


async def charge_fee_for_task_assignment(task_public_id: str, account_public_id: str):
    async with _task_billing_transaction(task_public_id, account_public_id) as (task, billing_context):
        transaction: BillingTransaction = await billing_context.create_transaction(debit=0, credit=task.assignment_cost)
        billing_context.session.add(TaskAssignment(billing_transaction_id=transaction.id, task_id=task.id))
        await billing_context.session.commit()
    await _emit_event_task_transaction_completed(billing_context, transaction, 'task_assignment', task)


async def assess_amount_for_task_closing(task_public_id, account_public_id):
    async with _task_billing_transaction(task_public_id, account_public_id) as (task, billing_context):
        transaction = await billing_context.create_transaction(debit=task.closing_cost, credit=0)
        billing_context.session.add(TaskClosing(billing_transaction_id=transaction.id, task_id=task.id))
        await billing_context.session.commit()
    await _emit_event_task_transaction_completed(billing_context, transaction, 'task_closing', task)
