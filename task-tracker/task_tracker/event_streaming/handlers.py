import logging

from sqlalchemy import select

import event_streaming
from task_tracker import database
from task_tracker.models import Account, AccountRole

logger = logging.getLogger(__name__)


@event_streaming.on_event('AccountCreated')
async def on_account_created(event_data):
    logger.info('AccountCreated: %s', event_data)
    # public_id is NONE
    # async with database.create_session() as session:
    #     account = Account(**event_data)
    #    session.add(account)
    #    await session.commit()


@event_streaming.on_event('AccountUpdated')
async def on_account_updated(event_data):
    logger.info('AccountUpdated: %s', event_data)
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
async def on_account_role_changed(event_data):
    logger.info('AccountRoleChanged: %s', event_data)
    async with database.create_session() as session:
        query_result = await session.execute(
            select(Account).where(Account.public_id == event_data['public_id'])
        )
        account: Account | None = query_result.scalars().first()
        if account:
            account.role = AccountRole(event_data['role'])
            await session.commit()
