import argparse
import logging
from typing import Any

from utils.mqtt_manager import MQTTManager

MAX_NODES = 40

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    """Interactive UI to control multiple OWL nodes via MQTT."""
    parser = argparse.ArgumentParser(description="MQTT UI for multiple OWL nodes")
    parser.add_argument("--host", default="localhost", help="MQTT broker host")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--nodes", type=int, default=1, help="Number of OWL nodes (1-40)")
    args = parser.parse_args()

    if not 1 <= args.nodes <= MAX_NODES:
        parser.error(f"--nodes must be between 1 and {MAX_NODES}")

    manager = MQTTManager(host=args.host, port=args.port)
    try:
        manager.connect()
    except Exception as exc:  # pragma: no cover - network access only
        logger.error("Failed to connect to MQTT broker: %s", exc)
        return

    manager.start_loop()

    print(f"Connected to MQTT broker at {args.host}:{args.port}")

    menu = (
        "\nCommands:\n"
        " 1 - start detections on a node\n"
        " 2 - stop detections on a node\n"
        " 3 - shutdown a node\n"
        " 4 - turn all relays on\n"
        " 5 - turn all relays off\n"
        " 0 - quit UI\n"
    )

    try:
        while True:
            print(menu)
            try:
                choice = input("Select option: ").strip()
            except EOFError:
                break

            if choice == "0":
                break
            if choice in {"1", "2", "3"}:
                try:
                    node = int(input("Node id: ").strip())
                except ValueError:
                    print("Invalid node id")
                    continue
                if not 1 <= node <= args.nodes:
                    print(f"Node id must be between 1 and {args.nodes}")
                    continue
                cmd_map = {"1": "start", "2": "stop", "3": "shutdown"}
                manager.publish_to_topic(
                    f"owl/{node}/control", {"command": cmd_map[choice]}
                )
                continue
            if choice == "4":
                for node in range(1, args.nodes + 1):
                    manager.publish_to_topic(f"owl/{node}/control", {"command": "all_on"})
                continue
            if choice == "5":
                for node in range(1, args.nodes + 1):
                    manager.publish_to_topic(f"owl/{node}/control", {"command": "all_off"})
                continue

            print("Unknown option")
    finally:
        manager.disconnect()
        print("Disconnected from broker")


if __name__ == "__main__":
    main()
