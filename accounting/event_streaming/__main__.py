import asyncio
import logging

import event_streaming
from task_tracker import database
import task_tracker.event_streaming.handlers  # noqa

topics = 'accounts-stream', 'task-stream', 'task-lifecycle'
group = 'task-tracker'

logging.basicConfig(level=logging.INFO)


async def main():
    await database.setup(database.Settings())
    await event_streaming.consume(event_streaming.Settings(), topics, group)

asyncio.run(main(), debug=True)
