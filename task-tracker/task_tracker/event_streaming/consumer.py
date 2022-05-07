from collections import defaultdict
import json

from aiokafka import AIOKafkaConsumer

from task_tracker.event_streaming.config import Settings


def event_handler(event_name):
    def decorator(handler):
        event_handler.registry[event_name].append(handler)
        return handler
    return decorator


event_handler.registry = defaultdict(list)


async def run(settings: Settings, topics, group):
    consumer = AIOKafkaConsumer(
        *topics,
        bootstrap_servers=settings.bootstrap_servers,
        group_id=group,
    )
    await consumer.start()
    try:
        async for message in consumer:
            message = json.loads(message.value)
            for handler in event_handler.registry[message['event_name']]:
                await handler(message['data'])
    finally:
        await consumer.stop()
