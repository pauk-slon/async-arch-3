import asyncio
import logging

import database
import event_streaming
import analytics.event_consuming.handlers  # noqa

topics = 'accounts-stream', 'accounts',  'task-stream', 'task-price-stream', 'billing-transactions'
group = 'analytics'

logging.basicConfig(level=logging.INFO)


async def main():
    await database.setup(database.Settings())
    event_streaming_settings = event_streaming.Settings()
    await event_streaming.consume(event_streaming_settings, topics, group)


asyncio.run(main(), debug=True)
