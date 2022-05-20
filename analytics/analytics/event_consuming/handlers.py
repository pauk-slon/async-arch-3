from typing import Any, Mapping
import logging

import database
import event_streaming
from analytics.models import Account, AccountRole
from db_utils import get_or_create

logger = logging.getLogger(__name__)


@event_streaming.on_event('AccountCreated')
@event_streaming.on_event('AccountUpdated')
async def on_account_updated(event_name: str, event_version: int, event_data: Mapping[str, Any]):
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
async def on_account_role_changed(event_name: str, event_version: int, event_data: Mapping[str, Any]):
    logger.info('%s: %s', event_name, event_data)
    async with database.create_session() as session:
        public_id = event_data['public_id']
        account, _created = await get_or_create(session, Account, public_id=public_id)
        account.role = AccountRole(event_data['role'])
        await session.commit()
        await session.refresh(account)
