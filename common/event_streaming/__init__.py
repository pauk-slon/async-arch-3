from collections import defaultdict
import datetime
import json
import uuid

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from pydantic import BaseSettings

from event_streaming.schema_registry import SchemaRegistry


class Settings(BaseSettings):
    bootstrap_servers: str
    schemas_directory: str

    class Config:
        env_prefix = 'event_streaming_'


class Producer:
    def __init__(self, name: str):
        self._name = name
        self._schema_registry = SchemaRegistry()
        self._producer: AIOKafkaProducer | None = None

    async def start(self, settings: Settings):
        self._schema_registry.load_schemas(settings.schemas_directory)
        self._producer = AIOKafkaProducer(bootstrap_servers=settings.bootstrap_servers)
        await self._producer.start()

    async def stop(self):
        await self._producer.stop()

    async def send(self, topic_name: str, event_name: str, data: dict):
        message = {
            'event_id': str(uuid.uuid4()),
            'event_name': event_name,
            'event_time': datetime.datetime.now().isoformat(),
            'event_version': 1,
            'producer': self._name,
            'data': data,
        }
        self._schema_registry.validate_event(event_name, 1, message)
        await self._producer.send_and_wait(topic_name, json.dumps(message).encode())


def on_event(event_name):
    def decorator(handler):
        on_event.registry[event_name].add(handler)
        return handler

    return decorator


on_event.registry = defaultdict(set)


async def consume(settings: Settings, topics, group):
    schema_registry = SchemaRegistry()
    schema_registry.load_schemas(settings.schemas_directory)
    consumer = AIOKafkaConsumer(
        *topics,
        bootstrap_servers=settings.bootstrap_servers,
        group_id=group,
    )
    await consumer.start()
    try:
        async for message in consumer:
            message = json.loads(message.value)
            event_name = message['event_name']
            event_version = message.get('event_version', 1)
            for handler in on_event.registry[event_name]:
                schema_registry.validate_event(event_name, event_version, message)
                await handler(message['event_name'], message['data'])
    finally:
        await consumer.stop()
