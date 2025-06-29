# MQTT Section Control Guide

This document describes the MQTT protocol for interoperability between AgOpenGPS Section Control and OpenWeedLocator.

## Topics
- `agopen/sectioncontrol/commands` – receive section commands
- `agopen/sectioncontrol/status` – publish acknowledgements and heartbeat
- `agopen/system/commands` – system wide control such as shutdown

## Payloads
All messages use JSON. Examples:

```json
{"command":"set_section","section":2,"state":"on"}
{"command":"shutdown"}
{"status":"online","program":"OpenWeedLocator","timestamp":1720000000}
```

### Acknowledgements
Commands must be acknowledged via the status topic, for example:

```json
{"ack":"set_section","section":2,"state":"on"}
```

### Errors
If a command cannot be executed, publish an error message:

```json
{"error":"section_out_of_range","section":99}
```

## Behaviour
- Publish a heartbeat every 30 seconds with the `status` payload.
- On a shutdown command from `agopen/system/commands`, all relays are turned off and the program exits.
- Section commands update relay states immediately and send an acknowledgement.
