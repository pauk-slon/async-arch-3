import asyncio
import logging

from task_tracker import database
from task_tracker.event_streaming import consumer
from task_tracker.event_streaming.config import Settings
import task_tracker.event_streaming.handlers  # noqa

topics = 'accounts-stream', 'accounts'
group = 'task-tracker'

logging.basicConfig(level=logging.INFO)


async def main():
    await database.setup(database.Settings())
    await consumer.run(Settings(), topics, group)

asyncio.run(main(), debug=True)
