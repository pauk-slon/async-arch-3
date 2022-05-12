import asyncio
import logging

from task_tracker import database
from task_tracker.event_streaming import aiokafka
import task_tracker.event_streaming.handlers  # noqa

topics = 'accounts-stream', 'accounts'
group = 'task-tracker'

logging.basicConfig(level=logging.INFO)


async def main():
    await database.setup(database.Settings())
    await aiokafka.consume(aiokafka.Settings(), topics, group)

asyncio.run(main(), debug=True)
