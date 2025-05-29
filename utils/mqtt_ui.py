import logging
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional

from utils.mqtt_manager import MQTTManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Maximum number of OWL nodes supported by the UI
MAX_NODES = 40


class OwlMQTTGUI(tk.Tk):
    """Simple Tkinter GUI for controlling multiple OWL nodes via MQTT."""

    def __init__(self) -> None:
        super().__init__()

        self.title("OWL MQTT Control UI")
        self.geometry("400x300")
        self.resizable(False, False)

        # UI variables
        self.host_var = tk.StringVar(value="localhost")
        self.port_var = tk.IntVar(value=1883)
        self.nodes_var = tk.IntVar(value=1)
        self.node_id_var = tk.IntVar(value=1)

        # MQTT Manager instance
        self.manager: Optional[MQTTManager] = None

        self._create_widgets()

    def _create_widgets(self) -> None:
        """Create widgets for the application."""

        config_frame = ttk.LabelFrame(self, text="MQTT Broker Configuration")
        config_frame.pack(padx=10, pady=10, fill="x")

        ttk.Label(config_frame, text="Host:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        ttk.Entry(config_frame, textvariable=self.host_var, width=20).grid(
            row=0, column=1, padx=5, pady=5, sticky="w"
        )

        ttk.Label(config_frame, text="Port:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        ttk.Entry(config_frame, textvariable=self.port_var, width=20).grid(
            row=1, column=1, padx=5, pady=5, sticky="w"
        )

        ttk.Label(config_frame, text="Number of nodes:").grid(
            row=2, column=0, sticky="e", padx=5, pady=5
        )
        ttk.Entry(config_frame, textvariable=self.nodes_var, width=20).grid(
            row=2, column=1, padx=5, pady=5, sticky="w"
        )

        btn_frame = ttk.Frame(config_frame)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=5)
        ttk.Button(btn_frame, text="Connect", command=self.connect_to_broker).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Disconnect", command=self.disconnect_from_broker).pack(side="left", padx=5)

        commands_frame = ttk.LabelFrame(self, text="Node Commands")
        commands_frame.pack(padx=10, pady=10, fill="x")

        ttk.Label(commands_frame, text="Node ID:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        ttk.Entry(commands_frame, textvariable=self.node_id_var, width=10).grid(
            row=0, column=1, padx=5, pady=5, sticky="w"
        )

        ttk.Button(commands_frame, text="Start Detection", command=self.start_detection).grid(
            row=1, column=0, columnspan=2, sticky="ew", padx=5, pady=2
        )
        ttk.Button(commands_frame, text="Stop Detection", command=self.stop_detection).grid(
            row=2, column=0, columnspan=2, sticky="ew", padx=5, pady=2
        )
        ttk.Button(commands_frame, text="Shutdown Node", command=self.shutdown_node).grid(
            row=3, column=0, columnspan=2, sticky="ew", padx=5, pady=2
        )

        ttk.Separator(commands_frame, orient="horizontal").grid(
            row=4, column=0, columnspan=2, sticky="ew", pady=5
        )

        ttk.Button(commands_frame, text="All Relays ON", command=self.all_on).grid(
            row=5, column=0, columnspan=2, sticky="ew", padx=5, pady=2
        )
        ttk.Button(commands_frame, text="All Relays OFF", command=self.all_off).grid(
            row=6, column=0, columnspan=2, sticky="ew", padx=5, pady=2
        )

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # ------------------------------------------------------------------
    # Broker connection helpers
    # ------------------------------------------------------------------
    def connect_to_broker(self) -> None:
        """Connect to the MQTT broker."""
        host = self.host_var.get().strip()
        port = self.port_var.get()
        num_nodes = self.nodes_var.get()

        if not host:
            messagebox.showerror("Error", "Please specify an MQTT host.")
            return

        if not (1 <= num_nodes <= MAX_NODES):
            messagebox.showerror(
                "Error",
                f"Number of nodes must be between 1 and {MAX_NODES}.",
            )
            return

        if self.manager is not None:
            messagebox.showinfo("Info", "Already connected.")
            return

        try:
            self.manager = MQTTManager(host=host, port=port)
            self.manager.connect()
            self.manager.start_loop()
            messagebox.showinfo("Connected", f"Connected to MQTT broker at {host}:{port}")
        except Exception as exc:
            logger.error("Failed to connect to MQTT broker: %s", exc)
            messagebox.showerror("Connection Error", str(exc))
            self.manager = None

    def disconnect_from_broker(self) -> None:
        """Disconnect from the MQTT broker."""
        if self.manager:
            self.manager.disconnect()
            self.manager = None
            messagebox.showinfo("Disconnected", "Disconnected from MQTT broker.")
        else:
            messagebox.showinfo("Info", "No active connection.")

    # ------------------------------------------------------------------
    # Node command handlers
    # ------------------------------------------------------------------
    def start_detection(self) -> None:
        node_id = self._get_valid_node_id()
        if node_id is not None:
            self._publish_command(node_id, "start")

    def stop_detection(self) -> None:
        node_id = self._get_valid_node_id()
        if node_id is not None:
            self._publish_command(node_id, "stop")

    def shutdown_node(self) -> None:
        node_id = self._get_valid_node_id()
        if node_id is not None:
            self._publish_command(node_id, "shutdown")

    def all_on(self) -> None:
        if not self._verify_manager():
            return
        for node in range(1, self.nodes_var.get() + 1):
            self.manager.publish_to_topic(f"owl/{node}/control", {"command": "all_on"})

    def all_off(self) -> None:
        if not self._verify_manager():
            return
        for node in range(1, self.nodes_var.get() + 1):
            self.manager.publish_to_topic(f"owl/{node}/control", {"command": "all_off"})

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _publish_command(self, node_id: int, command: str) -> None:
        if not self._verify_manager():
            return
        self.manager.publish_to_topic(f"owl/{node_id}/control", {"command": command})
        logger.info("Published '%s' to node %s", command, node_id)

    def _verify_manager(self) -> bool:
        if not self.manager:
            messagebox.showerror("Error", "Not connected to any MQTT broker.")
            return False
        return True

    def _get_valid_node_id(self) -> Optional[int]:
        try:
            node_id = int(self.node_id_var.get())
        except (TypeError, ValueError):
            messagebox.showerror("Error", "Invalid Node ID.")
            return None

        if not (1 <= node_id <= self.nodes_var.get()):
            messagebox.showerror(
                "Error",
                f"Node ID must be between 1 and {self.nodes_var.get()}.",
            )
            return None
        return node_id

    def on_close(self) -> None:
        self.disconnect_from_broker()
        self.destroy()


def main() -> None:
    app = OwlMQTTGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
