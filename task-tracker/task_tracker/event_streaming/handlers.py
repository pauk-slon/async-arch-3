import logging
from typing import Any, Mapping

from sqlalchemy import select

import event_streaming
from task_tracker import database
from task_tracker.models import Account, AccountRole

logger = logging.getLogger(__name__)


@event_streaming.on_event('AccountCreated')
@event_streaming.on_event('AccountUpdated')
async def on_account_updated(event_name: str, event_data: Mapping[str, Any]):
    logger.info('%s: %s', event_name, event_data)
    if not event_data.get('public_id'):
        logger.warning('Invalid data, public_id is required!')
        return
    async with database.create_session() as session:
        query_result = await session.execute(
            select(Account).where(Account.public_id == event_data['public_id'])
        )
        account: Account | None = query_result.scalars().first()
        if account:
            for field in account.dict():
                if field in event_data:
                    setattr(account, field, event_data[field])
        else:
            account = Account(**event_data)
        session.add(account)
        await session.commit()


@event_streaming.on_event('AccountRoleChanged')
async def on_account_role_changed(event_name: str, event_data: Mapping[str, Any]):
    logger.info('%s: %s', event_name, event_data)
    async with database.create_session() as session:
        query_result = await session.execute(
            select(Account).where(Account.public_id == event_data['public_id'])
        )
        account: Account | None = query_result.scalars().first()
        if account:
            account.role = AccountRole(event_data['role'])
            await session.commit()
