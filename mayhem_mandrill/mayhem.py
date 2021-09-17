import asyncio
import logging
import random
import string
import uuid
import functools

import attr


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s,%(msecs)d %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)


@attr.s
class PubSubMessage:
    instance_name = attr.ib()
    message_id    = attr.ib(repr=False)
    hostname      = attr.ib(repr=False, init=False)
    restarted = attr.ib(repr=False, default=False)
    saved = attr.ib(repr=False, default=False)
    acked = attr.ib(repr=False, default=False)
    extended_cnt = attr.ib(repr=False, default=0)

    def __attrs_post_init__(self):
        self.hostname = f"{self.instance_name}.example.net"


async def restart_host(msg):
    """
    Restart a given host.

    args:
        msg (PubSubMessage): consumed event message for a particular host to be restarted.
    """
    # simulates variable time it takes to restart a host
    await asyncio.sleep(random.random())
    msg.restarted = True
    logging.info(f"Restarted {msg.hostname}")


async def save(msg):
    """
    Save something to a database.

    args:
        msg (PubSubMessage): consumed event message for a particular host to be restarted.
    """
    # simulates variable time it takes to persist a record to a database
    await asyncio.sleep(random.random())
    msg.saved = True
    logging.info(f"Saved {msg} into database")


async def cleanup(msg):
    """
    Cleanup tasks related to completing work on a message.

    args:
        msg (PubSubMessage): consumed event message that is done being
            processed.
        fut (asyncio.Future): future provided by the callback.
    """
    # blocks rest of the coroutine until `event.set` is called
    await event.wait()
    await asyncio.sleep(random.random())
    msg.acked = True
    logging.info(f"Done. Acked {msg}")


async def extend(msg, event):
    """
    Periodically extend the message acknowledgement deadline.

    args:
        msg (PubSubMessage): consumed event message to extend.
        event (asyncio.Event): event to watch for message extension or cleaning up.
    """
    while not event.is_set():
        msg.extended_cnt += 1
        logging.info(f"Extended deadline by 3 seconds for {msg}")
        await asyncio.sleep(2)


async def handle_message(msg):
    """
    Kick off tasks for a given message.

    args:
        msg (PubSubMessage): consumed message to process.
    """
    event = asyncio.Event()
    asyncio.create_task(extend(msg, event))
    await asyncio.gather(save(msg), restart_host(msg))
    event.set()


async def consume(queue):
    """
    Simulates a consumer that restarts a host when it receives a message

    args:
        queue (asyncio.Queue): Queue to consume messages from.
    """
    while True:
        msg = await queue.get()
        logging.info(f"Consumed {msg}")

        # restarting a host and saving an obj to the database using that host are treated as separate, independent
        # processes. if they were dependent you would await these coroutines sequentially
        asyncio.create_task(handle_message(msg))


async def publish(queue):
    """
    Simulates an external publisher of messages.

    args:
        queue (asyncio.Queue): Queue to publish messages to.
    """
    choices = string.ascii_lowercase + string.digits

    while True:
        msg_id = str(uuid.uuid4())
        host_id = "".join(random.choices(choices, k=4))
        instance_name = f"cattle-{host_id}"
        msg = PubSubMessage(message_id=msg_id, instance_name=instance_name)
        # publish an item
        asyncio.create_task(queue.put(msg))
        logging.debug(f"Published message {msg}")
        # simulate randomness of publishing messages
        await asyncio.sleep(random.random())


def main():
    queue = asyncio.Queue()
    loop = asyncio.get_event_loop()

    try:
        loop.create_task(publish(queue))
        loop.create_task(consume(queue))
        loop.run_forever()
    except KeyboardInterrupt:
        logging.info("Process interrupted")
    finally:
        loop.close()
        logging.info("Successfully shutdown the Mayhem service.")


if __name__ == "__main__":
    main()
