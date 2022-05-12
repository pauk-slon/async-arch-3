from collections import defaultdict
import json

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from pydantic import BaseSettings


class Settings(BaseSettings):
    bootstrap_servers: str

    class Config:
        env_prefix = 'event_streaming_'


class Producer:
    def __init__(self):
        self._producer: AIOKafkaProducer | None = None

    async def start(self, settings: Settings):
        self._producer = AIOKafkaProducer(bootstrap_servers=settings.bootstrap_servers)
        await self._producer.start()

    async def stop(self):
        await self._producer.stop()

    async def send(self, topic_name: str, event_name: str, data: dict):
        message = json.dumps({'event_name': event_name, 'data': data})
        await self._producer.send_and_wait(topic_name, message.encode())


producer = Producer()


def event_handler(event_name):
    def decorator(handler):
        event_handler.registry[event_name].append(handler)
        return handler

    return decorator


event_handler.registry = defaultdict(list)


async def consume(settings: Settings, topics, group):
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
