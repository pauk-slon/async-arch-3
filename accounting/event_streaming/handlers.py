from typing import Any, Mapping, Protocol, Type, TypeVar
import logging

from sqlalchemy import select

import event_streaming
from accounting import database
from accounting.models import Account, AccountRole, Task, SQLModel

logger = logging.getLogger(__name__)


class StreamedModelProtocol(Protocol):
    public_id: str

    def __init__(self, **defaults):
        pass


ModelT = TypeVar('ModelT', bound=SQLModel)


async def get_or_create(session, model: Type[ModelT], defaults=None, **filter_kwargs) -> (ModelT, bool):
    instance: model | None = (await session.execute(select(Task).filter_by(**filter_kwargs))).scalar_one_or_none()
    created = False
    if not instance:
        instance_kwargs = defaults | filter_kwargs if defaults else filter_kwargs
        instance = model(**instance_kwargs)
        session.add(instance)
        created = True
    return instance, created


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
    async with database.create_session() as session:
        task, _created = await get_or_create(session, Task, public_id=public_id)
        task.price()
        await session.commit()
