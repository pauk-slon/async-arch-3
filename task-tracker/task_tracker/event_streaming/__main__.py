import asyncio
import logging

import database
import event_streaming
import task_tracker.event_streaming.handlers  # noqa

topics = 'accounts-stream', 'accounts'
group = 'task-tracker'

logging.basicConfig(level=logging.INFO)


async def main():
    await database.setup(database.Settings())
    await event_streaming.consume(event_streaming.Settings(), topics, group)

asyncio.run(main(), debug=True)
