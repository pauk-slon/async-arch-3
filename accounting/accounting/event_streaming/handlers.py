from typing import Any, Mapping
import logging

import event_streaming
from accounting import database
from accounting.models import Account, AccountRole, Task
from accounting.transactions.billing import initialize_account
from accounting.transactions.tasks import price_task, charge_fee_for_task_assignment, assess_amount_for_task_completion
from accounting.transactions.utils import get_or_create

logger = logging.getLogger(__name__)


@event_streaming.on_event('AccountCreated')
@event_streaming.on_event('AccountUpdated')
async def on_account_updated(event_name: str, event_data: Mapping[str, Any]):
    logger.info('%s: %s', event_name, event_data)
    if not event_data.get('public_id'):
        logger.warning('Invalid data, public_id is required!')
        return
    public_id = event_data['public_id']
    async with database.create_session() as session:
        account, created = await get_or_create(session, Account, public_id=public_id, defaults=event_data)
        if not created:
            for field in account.dict():
                if field in event_data:
                    setattr(account, field, event_data[field])
        await session.commit()


@event_streaming.on_event('AccountRoleChanged')
async def on_account_role_changed(event_name: str, event_data: Mapping[str, Any]):
    logger.info('%s: %s', event_name, event_data)
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
async def on_task_updated(event_name: str, event_data: Mapping[str, Any]):
    logger.info('%s: %s', event_name, event_data)
    public_id = event_data['public_id']
    async with database.create_session() as session:
        task, _created = await get_or_create(session, Task, public_id=public_id)
        task.description = f"{event_data['title']}\n{event_data['description']}"
        await session.commit()


@event_streaming.on_event('TaskAdded')
async def on_task_added(event_name: str, event_data: Mapping[str, Any]):
    logger.info('%s: %s', event_name, event_data)
    public_id = event_data['task']
    await price_task(public_id)


@event_streaming.on_event('TaskAssigned')
@event_streaming.on_event('TaskClosed')
async def on_task_assigned(event_name: str, event_data: Mapping[str, Any]):
    logger.info('%s: %s', event_name, event_data)
    task = event_data['task']
    await price_task(task)  # if TaskAdded is haven't gotten yet
    account = event_data['assignee']
    await initialize_account(account)
    if event_name == 'TaskAssigned':
        await charge_fee_for_task_assignment(task, account)
    elif event_name == 'TaskClosed':
        await assess_amount_for_task_completion(task, account)
