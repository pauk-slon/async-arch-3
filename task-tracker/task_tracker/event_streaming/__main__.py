import asyncio
import logging

from task_tracker.event_streaming import consumer
from task_tracker.event_streaming.config import Settings
import task_tracker.event_streaming.handlers  # noqa

topics = 'accounts-stream', 'accounts'
group = 'task-tracker'

logging.basicConfig(level=logging.INFO)

asyncio.run(consumer.run(Settings(), topics, group), debug=True)
