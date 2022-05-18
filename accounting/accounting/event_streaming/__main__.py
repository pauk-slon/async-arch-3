import asyncio
import logging

import event_streaming
from accounting import database
import accounting.event_streaming.handlers  # noqa

topics = 'accounts-stream', 'accounts', 'task-stream', 'task-lifecycle',
group = 'accounting'

logging.basicConfig(level=logging.INFO)


async def main():
    await database.setup(database.Settings())
    await event_streaming.consume(event_streaming.Settings(), topics, group)

asyncio.run(main(), debug=True)
