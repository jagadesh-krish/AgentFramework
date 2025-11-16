import asyncio
import json
import os
from typing import AsyncGenerator, Optional

import aio_pika


class RabbitMQBus:
    def __init__(self) -> None:
        self.url = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
        self._connection: Optional[aio_pika.RobustConnection] = None
        self._channel: Optional[aio_pika.abc.AbstractChannel] = None

    async def connect(self) -> None:
        if self._connection and not self._connection.is_closed:
            return
        self._connection = await aio_pika.connect_robust(self.url)
        self._channel = await self._connection.channel()

    async def close(self) -> None:
        try:
            if self._channel and not self._channel.is_closed:
                await self._channel.close()
        finally:
            if self._connection and not self._connection.is_closed:
                await self._connection.close()

    async def publish(self, queue_name: str, message: dict) -> None:
        assert self._channel is not None
        queue = await self._channel.declare_queue(queue_name, durable=True)
        body = json.dumps(message).encode("utf-8")
        await self._channel.default_exchange.publish(
            aio_pika.Message(body=body, content_type="application/json"), routing_key=queue.name
        )

    async def consume(self, queue_name: str) -> AsyncGenerator[dict, None]:
        assert self._channel is not None
        queue = await self._channel.declare_queue(queue_name, durable=True)
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    try:
                        data = json.loads(message.body.decode("utf-8"))
                    except Exception:
                        data = {"raw": message.body.decode("utf-8", errors="ignore")}
                    yield data


# Queue names
REQUEST_QUEUE = os.environ.get("REQUEST_QUEUE", "agent_requests")
RESPONSE_QUEUE = os.environ.get("RESPONSE_QUEUE", "agent_responses")


