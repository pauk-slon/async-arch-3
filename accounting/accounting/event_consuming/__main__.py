import asyncio
import logging

import database
import event_streaming
from accounting import event_producing
import accounting.event_consuming.handlers  # noqa

topics = 'accounts-stream', 'accounts', 'task-stream', 'task-lifecycle',
group = 'accounting'

logging.basicConfig(level=logging.INFO)


async def main():
    await database.setup(database.Settings())
    event_streaming_settings = event_streaming.Settings()
    await event_producing.producer.start(event_streaming_settings)
    try:
        await event_streaming.consume(event_streaming_settings, topics, group)
    finally:
        await event_producing.producer.stop()

asyncio.run(main(), debug=True)
