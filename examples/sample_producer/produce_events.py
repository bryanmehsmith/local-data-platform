"""Simulates a streaming source publishing click/view events to Redpanda.

Usage:
    python produce_events.py --count 100 --brokers localhost:19092
"""

import argparse
import json
import random
import uuid
from datetime import datetime, timezone

from kafka import KafkaProducer

TOPIC = "raw.events"
EVENT_TYPES = ["click", "view", "purchase"]


def make_event() -> dict:
    return {
        "event_id": str(uuid.uuid4()),
        "user_id": random.randint(1, 20),
        "event_type": random.choice(EVENT_TYPES),
        "ts": datetime.now(timezone.utc).isoformat(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--brokers", default="localhost:19092")
    args = parser.parse_args()

    producer = KafkaProducer(
        bootstrap_servers=args.brokers,
        key_serializer=lambda k: k.encode("utf-8"),
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )

    for _ in range(args.count):
        event = make_event()
        producer.send(TOPIC, key=event["event_id"], value=event)

    producer.flush()
    print(f"Produced {args.count} events to topic '{TOPIC}'")


if __name__ == "__main__":
    main()
