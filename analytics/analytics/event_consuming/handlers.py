from typing import Any, Mapping

import database
import event_streaming
from analytics.models import Account, AccountRole, Task, BillingTransaction, BillingTransactionType
from db_utils import get_or_create


@event_streaming.on_event('AccountCreated')
@event_streaming.on_event('AccountUpdated')
async def on_account_updated(event_name: str, event_version: int, event_data: Mapping[str, Any]):
    async with database.create_session() as session:
        account, created = await get_or_create(session, Account, public_id=event_data['public_id'], defaults=event_data)
        if not created:
            for field in account.dict():
                if field in event_data:
                    setattr(account, field, event_data[field])
        await session.commit()


@event_streaming.on_event('AccountRoleChanged')
async def on_account_role_changed(event_name: str, event_version: int, event_data: Mapping[str, Any]):
    async with database.create_session() as session:
        account, _created = await get_or_create(session, Account, public_id=event_data['public_id'])
        account.role = AccountRole(event_data['role'])
        await session.commit()
        await session.refresh(account)


@event_streaming.on_event('TaskCreated')
@event_streaming.on_event('TaskUpdated')
async def on_task_updated(event_name: str, event_version: int, event_data: Mapping[str, Any]):
    async with database.create_session() as session:
        task, _created = await get_or_create(session, Task, public_id=event_data['public_id'])
        if event_version == 1:  # Drop support for v1 after releasing of v2-producer
            task.description = f"{event_data['title']}\n{event_data['description']}"
        elif event_version == 2:
            jira_id = event_data['jira_id']
            jira_prefix = jira_id and f'[{jira_id}] '
            task.description = f"{jira_prefix}{event_data['title']}\n{event_data['description']}"
        await session.commit()


@event_streaming.on_event('TaskPriceCreated')
async def on_task_updated(event_name: str, event_version: int, event_data: Mapping[str, Any]):
    async with database.create_session() as session:
        task, _created = await get_or_create(session, Task, public_id=event_data['task'])
        task.assignment_cost = event_data['assignment_cost']
        task.closing_cost = event_data['closing_cost']
        await session.commit()


@event_streaming.on_event('BillingTransactionCompleted')
async def on_billing_transaction_completed(event_name: str, event_version: int, event_data: Mapping[str, Any]):
    async with database.create_session() as session:
        account, _account_created = await get_or_create(session, Account, public_id=event_data['account'])
        billing_transaction_type = BillingTransactionType(event_data['details']['type'])
        if billing_transaction_type in {BillingTransactionType.task_assignment, BillingTransactionType.task_closing}:
            task, _task_created = await get_or_create(session, Task, public_id=event_data['details']['task'])
        session.add(BillingTransaction(
            public_id=event_data['public_id'],
            date=event_data['date'],
            business_day=event_data['business_day'],
            account_id=account.id,
            type=billing_transaction_type,
            debit=event_data['debit'],
            credit=event_data['credit'],
            task_id=task.id,
        ))
        await session.commit()
