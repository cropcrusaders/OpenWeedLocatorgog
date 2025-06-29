import argparse
import json
import logging
import threading
import time
from configparser import ConfigParser
from pathlib import Path
from typing import Dict

from utils.mqtt_manager import MQTTManager
from utils.output_manager import RelayControl


STATUS_TOPIC = "agopen/sectioncontrol/status"
COMMAND_TOPIC = "agopen/sectioncontrol/commands"
SYSTEM_TOPIC = "agopen/system/commands"


class SectionControlMQTT:
    """MQTT interface for AgOpenGPS section control."""

    def __init__(self, host: str, port: int, config: Path):
        self.logger = logging.getLogger(__name__)
        self.host = host
        self.port = port
        self.config = config
        self.mqtt = MQTTManager(host=host, port=port)
        self.relay = self._load_relays(config)
        self.running = True
        self._hb_thread = threading.Thread(target=self._heartbeat_loop)

    def _load_relays(self, config_path: Path) -> RelayControl:
        parser = ConfigParser()
        parser.read(config_path)
        relay_num = parser.getint("System", "relay_num", fallback=0)
        relay_map: Dict[int, int] = {}
        for i in range(relay_num):
            pin = parser.getint("Relays", str(i), fallback=None)
            if pin is None:
                continue
            relay_map[i] = pin
        return RelayControl(relay_map)

    def start(self) -> None:
        self.mqtt.connect()
        self.mqtt.start_loop()
        self.mqtt.subscribe(COMMAND_TOPIC, self._on_message)
        self.mqtt.subscribe(SYSTEM_TOPIC, self._on_message)
        self.publish_status()
        self._hb_thread.start()
        self.logger.info("MQTT Section Control started")
        try:
            while self.running:
                time.sleep(0.1)
        finally:
            self.shutdown()

    def _on_message(self, client, userdata, msg) -> None:
        try:
            data = json.loads(msg.payload.decode())
        except json.JSONDecodeError:
            self._publish({"error": "invalid_json"})
            return

        topic = msg.topic
        cmd = data.get("command", "").lower()
        if topic == SYSTEM_TOPIC and cmd == "shutdown":
            self.logger.info("Shutdown command received")
            self._publish({"ack": "shutdown"})
            self.running = False
            return

        if topic == COMMAND_TOPIC and cmd == "set_section":
            section = data.get("section")
            state = data.get("state", "").lower()
            if not isinstance(section, int):
                self._publish({"error": "invalid_section"})
                return
            if state not in {"on", "off"}:
                self._publish({"error": "invalid_state"})
                return
            if section < 1 or section > len(self.relay.relay_dict):
                self._publish({"error": "section_out_of_range", "section": section})
                return
            idx = section - 1
            if state == "on":
                self.relay.relay_on(idx, verbose=False)
            else:
                self.relay.relay_off(idx, verbose=False)
            self._publish({"ack": "set_section", "section": section, "state": state})
            return

    def _publish(self, payload: Dict) -> None:
        self.mqtt.publish_to_topic(STATUS_TOPIC, payload)

    def publish_status(self) -> None:
        self._publish({
            "status": "online",
            "program": "OpenWeedLocator",
            "timestamp": int(time.time())
        })

    def _heartbeat_loop(self) -> None:
        while self.running:
            time.sleep(30)
            if not self.running:
                break
            self.publish_status()

    def shutdown(self) -> None:
        self.logger.info("Shutting down Section Control")
        self.relay.all_off()
        self.mqtt.disconnect()


def main() -> None:
    parser = argparse.ArgumentParser(description="MQTT Section Control bridge")
    parser.add_argument("--host", default="localhost", help="MQTT broker host")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument(
        "--config", default="config/DAY_SENSITIVITY_2.ini", help="OWL config file")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    sc = SectionControlMQTT(args.host, args.port, Path(args.config))
    sc.start()


if __name__ == "__main__":
    main()
