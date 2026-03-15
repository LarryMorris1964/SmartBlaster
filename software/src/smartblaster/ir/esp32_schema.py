"""Wire schema helpers for SmartBlaster Pi -> ESP32 IR bridge."""

from __future__ import annotations

import json
from typing import Any

from smartblaster.ir.command import MideaIrCommand

PROTOCOL_VERSION = 1
TOPIC = "midea_ir.command"
ACK_TOPIC = "midea_ir.ack"

ERR_BAD_JSON = "bad_json"
ERR_BAD_SCHEMA = "bad_schema"
ERR_UNSUPPORTED_VERSION = "unsupported_version"
ERR_INVALID_COMMAND = "invalid_command"
ERR_TX_FAILED = "tx_failed"


def encode_command_message(command: MideaIrCommand, request_id: str) -> str:
    envelope = {
        "v": PROTOCOL_VERSION,
        "topic": TOPIC,
        "request_id": request_id,
        "payload": command.to_payload(),
    }
    return json.dumps(envelope, separators=(",", ":")) + "\n"


def parse_command_message(raw: str) -> tuple[str, MideaIrCommand]:
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("command must be a JSON object")

    if data.get("v") != PROTOCOL_VERSION:
        raise ValueError(f"unsupported protocol version: {data.get('v')}")

    if data.get("topic") != TOPIC:
        raise ValueError(f"unsupported topic: {data.get('topic')}")

    request_id = data.get("request_id")
    if not isinstance(request_id, str) or not request_id.strip():
        raise ValueError("request_id must be a non-empty string")

    payload = data.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object")

    command = MideaIrCommand.from_payload(payload)
    return request_id, command


def encode_ack_message(
    request_id: str,
    *,
    ok: bool,
    error_code: str | None = None,
    error_message: str | None = None,
) -> str:
    ack: dict[str, Any] = {
        "v": PROTOCOL_VERSION,
        "topic": ACK_TOPIC,
        "request_id": request_id,
        "ok": ok,
    }
    if not ok:
        ack["error_code"] = error_code or ERR_TX_FAILED
        if error_message:
            ack["error_message"] = error_message
    return json.dumps(ack, separators=(",", ":")) + "\n"


def decode_ack_message(raw: str) -> dict[str, Any]:
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("ACK must be a JSON object")
    if "request_id" not in data or "ok" not in data:
        raise ValueError("ACK must include request_id and ok")
    if data.get("topic") not in (None, ACK_TOPIC):
        raise ValueError("ACK topic is invalid")
    return data
