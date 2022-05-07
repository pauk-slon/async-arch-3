import logging

from task_tracker.event_streaming import consumer

logger = logging.getLogger(__name__)


@consumer.event_handler('AccountCreated')
async def on_account_created(event_data):
    logger.info('AccountCreated: %s', event_data)


@consumer.event_handler('AccountUpdated')
async def on_account_updated(event_data):
    logger.info('AccountUpdated: %s', event_data)


@consumer.event_handler('AccountRoleChanged')
async def on_account_role_changed(event_data):
    logger.info('AccountRoleChanged: %s', event_data)
