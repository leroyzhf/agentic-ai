"""Lobster payload dropfile helper — the write side of the file contract
defined by OpenClaw Lobster (see protocol.py).

Producer apps (currently: xhs-auto-publisher, potentially:
morning-newspaper) call `emit_payload()` to hand off work to Lobster
without touching any Feishu credentials themselves.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .protocol import (
    CHANNEL_LOBSTER,
    FIXED_TZ_OFFSET_HOURS,
    PROTOCOL_VERSION,
)

_FIXED_TZ = timezone(timedelta(hours=FIXED_TZ_OFFSET_HOURS))


@dataclass
class LobsterPayload:
    """One payload for one Lobster handoff.

    Field names match the JSON schema in
    xhs-auto-publisher/docs/LOBSTER_NOTIFY_PROTOCOL.md — any rename here
    is a breaking change for the Lobster consumer.
    """

    kind: str                       # e.g. "login_qr"
    run_id: str                     # unique per producer task
    action: str                     # what the consumer must do
    title: str                      # human-readable header
    platform: str                   # producer's product (e.g. "xiaohongshu")
    message_lines: list[str]        # standalone display lines
    delivery: dict[str, Any]        # {type, path, caption_lines, ...}
    screenshot_path: str = ""       # optional; kept for backwards-compat
    channel: str = CHANNEL_LOBSTER
    protocol_version: str = PROTOCOL_VERSION
    ts: str = field(default_factory=lambda: datetime.now(_FIXED_TZ).isoformat())

    def to_dict(self) -> dict[str, Any]:
        # Field order matches the reference payload in LOBSTER_NOTIFY_PROTOCOL.md
        # so downstream diffs stay stable.
        return {
            "ts": self.ts,
            "channel": self.channel,
            "kind": self.kind,
            "platform": self.platform,
            "title": self.title,
            "run_id": self.run_id,
            "screenshot_path": self.screenshot_path,
            "message_lines": list(self.message_lines),
            "action": self.action,
            "delivery": dict(self.delivery),
            "protocol_version": self.protocol_version,
        }


def payload_dir_for(run_dir: Path, base: str = "runtime/lobster-notify") -> Path:
    """Compute the target directory for a Lobster payload.

    `run_dir` is the producer's per-task workspace (e.g.
    `runtime/runs/<run_id>`). If `base` is absolute, honour it verbatim;
    otherwise anchor it two levels up from `run_dir` (matching the
    existing xhs layout `runtime/lobster-notify/<run_id>/`).
    """
    base_path = Path(base)
    if not base_path.is_absolute():
        # `run_dir` = runtime/runs/<run_id> → its .parent.parent is the
        # project's runtime root, then append the last segment of `base`.
        base_path = run_dir.parent.parent / Path(base).name
    return base_path / run_dir.name


def emit_payload(
    payload: LobsterPayload,
    *,
    run_dir: Path,
    base_dir: str = "runtime/lobster-notify",
    filename: str | None = None,
) -> Path:
    """Serialize `payload` to `<base_dir>/<run_id>/<filename>` and return
    the written path. `filename` defaults to `<kind>.payload.json`.
    """
    target_dir = payload_dir_for(run_dir, base_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    name = filename or f"{payload.kind}.payload.json"
    path = target_dir / name
    path.write_text(
        json.dumps(payload.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path
