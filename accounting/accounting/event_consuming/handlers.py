from typing import Any, Mapping

import database
import event_streaming
from accounting.models import Account, AccountRole, Task
from accounting.transactions.billing import initialize_account
from accounting.transactions.tasks import price_task, charge_fee_for_task_assignment, assess_amount_for_task_closing
from db_utils import get_or_create


@event_streaming.on_event('AccountCreated')
@event_streaming.on_event('AccountUpdated')
async def on_account_updated(event_name: str, event_version: int, event_data: Mapping[str, Any]):
    public_id = event_data['public_id']
    async with database.create_session() as session:
        account, created = await get_or_create(session, Account, public_id=public_id, defaults=event_data)
        if not created:
            for field in account.dict():
                if field in event_data:
                    setattr(account, field, event_data[field])
        await session.commit()


@event_streaming.on_event('AccountRoleChanged')
async def on_account_role_changed(event_name: str, event_version: int, event_data: Mapping[str, Any]):
    async with database.create_session() as session:
        public_id = event_data['public_id']
        account, _created = await get_or_create(session, Account, public_id=public_id)
        account.role = AccountRole(event_data['role'])
        await session.commit()
        await session.refresh(account)
    if account.role == AccountRole.worker:
        await initialize_account(account.public_id)


@event_streaming.on_event('TaskCreated')
@event_streaming.on_event('TaskUpdated')
async def on_task_updated(event_name: str, event_version: int, event_data: Mapping[str, Any]):
    public_id = event_data['public_id']
    async with database.create_session() as session:
        task, _created = await get_or_create(session, Task, public_id=public_id)
        if event_version == 1:  # Drop support for v1 after releasing of v2-producer
            task.description = f"{event_data['title']}\n{event_data['description']}"
        elif event_version == 2:
            jira_id = event_data['jira_id']
            jira_prefix = jira_id and f'[{jira_id}] '
            task.description = f"{jira_prefix}{event_data['title']}\n{event_data['description']}"
        await session.commit()


@event_streaming.on_event('TaskAdded')
async def on_task_added(event_name: str, event_version: int, event_data: Mapping[str, Any]):
    public_id = event_data['task']
    await price_task(public_id)


@event_streaming.on_event('TaskAssigned')
@event_streaming.on_event('TaskClosed')
async def on_task_assigned(event_name: str, event_version: int, event_data: Mapping[str, Any]):
    task = event_data['task']
    await price_task(task)  # if TaskAdded is haven't gotten yet
    account = event_data['assignee']
    await initialize_account(account)
    if event_name == 'TaskAssigned':
        await charge_fee_for_task_assignment(task, account)
    elif event_name == 'TaskClosed':
        await assess_amount_for_task_closing(task, account)
