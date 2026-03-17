"""Structured activity logging for SmartBlaster.

All operational events — IR commands, scheduling triggers, camera verification
results, home automation commands, and system lifecycle events — are emitted as
structured JSON records via structlog.

Typical usage
-------------
Call ``configure_logging()`` once at process start (bootstrap), then create an
``ActivityLogger`` and inject it into components that need it.

    configure_logging(log_level="INFO", activity_log_file=Path("data/activity_log.jsonl"))
    log = ActivityLogger(device_name="Living Room")
    log.runtime_started(profile_id="midea_kjr_12b_dp_t", camera_enabled=True, dry_run=False)

The activity log file is a rotating JSONL file (one JSON object per line).
In tests, use ``structlog.testing.capture_logs()`` to assert on emitted events
without touching the filesystem.
"""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path
from typing import Any

import structlog

_ACTIVITY_LOGGER_NAME = "smartblaster.activity"
_LOG_MAX_BYTES = 5 * 1024 * 1024  # 5 MB per file
_LOG_BACKUP_COUNT = 5


def configure_logging(
    log_level: str = "INFO",
    activity_log_file: Path | None = None,
) -> None:
    """Configure stdlib logging and structlog for the process.

    Must be called once at process startup before any loggers are created.
    Subsequent calls reconfigure (useful in tests; use structlog.reset_defaults()
    between test cases when testing configure_logging itself).
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=False,
    )

    # Root logger handles console output (JSON, one record per line).
    logging.basicConfig(level=level, format="%(message)s", force=True)

    # Dedicated file handler on the activity logger for JSONL rotation.
    # propagate=True so events also appear on the console via root.
    if activity_log_file is not None:
        activity_log_file.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.handlers.RotatingFileHandler(
            activity_log_file,
            maxBytes=_LOG_MAX_BYTES,
            backupCount=_LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        fh.setFormatter(logging.Formatter("%(message)s"))
        act = logging.getLogger(_ACTIVITY_LOGGER_NAME)
        # Avoid adding duplicate handlers on repeated calls.
        if not any(isinstance(h, logging.handlers.RotatingFileHandler) for h in act.handlers):
            act.addHandler(fh)
        act.setLevel(logging.DEBUG)
        act.propagate = True


class ActivityLogger:
    """Typed structured logger for SmartBlaster operational events.

    Each method corresponds to a distinct event type and emits a JSON record
    with a fixed ``event`` key plus typed keyword fields.  Bind a device name
    at construction so every record identifies its origin.
    """

    def __init__(self, device_name: str = "SmartBlaster") -> None:
        self._log = structlog.get_logger(_ACTIVITY_LOGGER_NAME).bind(device=device_name)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def runtime_started(
        self, *, profile_id: str, camera_enabled: bool, dry_run: bool
    ) -> None:
        self._log.info(
            "runtime_started",
            profile_id=profile_id,
            camera_enabled=camera_enabled,
            dry_run=dry_run,
        )

    def runtime_stopped(self, *, reason: str = "shutdown") -> None:
        self._log.info("runtime_stopped", reason=reason)

    def setup_saved(self, *, device_name: str, profile_id: str) -> None:
        self._log.info("setup_saved", device_name=device_name, profile_id=profile_id)

    # ── State machine ─────────────────────────────────────────────────────────

    def state_changed(self, *, from_state: str, to_state: str, trigger: str) -> None:
        self._log.info(
            "state_changed",
            from_state=from_state,
            to_state=to_state,
            trigger=trigger,
        )

    # ── Scheduling ────────────────────────────────────────────────────────────

    def schedule_event(self, *, trigger: str, source: str = "weekly_schedule") -> None:
        """Log a scheduling trigger emitted by the runtime scheduler."""
        self._log.info("schedule_event", trigger=trigger, source=source)

    def async_event(self, *, trigger: str, source: str, **extra: Any) -> None:
        """Log an asynchronous external event (solar/inverter signal, etc.)."""
        self._log.info("async_event", trigger=trigger, source=source, **extra)

    # ── IR commands ───────────────────────────────────────────────────────────

    def ir_command_sent(
        self,
        *,
        request_id: str,
        command_name: str,
        criticality: str,
        max_attempts: int,
        dry_run: bool,
    ) -> None:
        self._log.info(
            "ir_command_sent",
            request_id=request_id,
            command_name=command_name,
            criticality=criticality,
            max_attempts=max_attempts,
            dry_run=dry_run,
        )

    def ir_command_verified(
        self,
        *,
        request_id: str,
        confidence: float,
        parsed_mode: str | None = None,
        parsed_temperature: float | None = None,
    ) -> None:
        self._log.info(
            "ir_command_verified",
            request_id=request_id,
            confidence=confidence,
            parsed_mode=parsed_mode,
            parsed_temperature=parsed_temperature,
        )

    def ir_command_verification_failed(
        self, *, request_id: str, reason: str
    ) -> None:
        self._log.warning(
            "ir_command_verification_failed",
            request_id=request_id,
            reason=reason,
        )

    # ── Home automation ───────────────────────────────────────────────────────

    def home_automation_command(
        self, *, integration: str, command: str, **payload: Any
    ) -> None:
        """Log a command received from a home automation integration.

        Examples::

            log.home_automation_command(integration="ifttt", command="cool_on")
            log.home_automation_command(integration="alexa", command="set_temperature", value=22)
        """
        self._log.info(
            "home_automation_command",
            integration=integration,
            command=command,
            **payload,
        )

    # ── Infrastructure ────────────────────────────────────────────────────────

    def reference_offload_run(
        self, *, scanned: int, offloaded: int, failed: int
    ) -> None:
        self._log.info(
            "reference_offload_run",
            scanned=scanned,
            offloaded=offloaded,
            failed=failed,
        )

    def network_failover(self, *, reason: str) -> None:
        self._log.warning("network_failover", reason=reason)
