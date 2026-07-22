from __future__ import annotations

from pathlib import Path
from typing import Any

from lobster_notify import LobsterPayload, emit_payload, payload_dir_for
from lobster_notify.protocol import (
    ACTION_SEND_IMAGE_TO_FEISHU_GROUP,
    DELIVERY_TYPE_IMAGE_FILE,
    KIND_LOGIN_QR,
)


class CloudNotifier:
    def __init__(self, app_config: dict[str, Any]) -> None:
        self.app_config = app_config

    def qr_handoff_enabled(self) -> bool:
        mode = str(self.app_config.get("notify_qr_via", "none")).lower()
        return mode == "lobster_channel"

    def notify_qr(self, screenshot_path: Path, *, run_dir: Path) -> None:
        mode = str(self.app_config.get("notify_qr_via", "none")).lower()
        if mode != "lobster_channel":
            raise RuntimeError(f"Unsupported cloud notify mode: {mode}")
        self._emit_lobster_channel_payload(screenshot_path, run_dir=run_dir)

    def _emit_lobster_channel_payload(self, screenshot_path: Path, *, run_dir: Path) -> None:
        message_lines = self._build_message_lines(screenshot_path, run_dir=run_dir)
        payload = LobsterPayload(
            kind=KIND_LOGIN_QR,
            run_id=run_dir.name,
            action=ACTION_SEND_IMAGE_TO_FEISHU_GROUP,
            title=f"{self._title_prefix()} 小红书登录二维码",
            platform=str(self.app_config.get("platform", "xiaohongshu")),
            message_lines=message_lines,
            screenshot_path=str(screenshot_path),
            delivery={
                "type": DELIVERY_TYPE_IMAGE_FILE,
                "path": str(screenshot_path),
                "caption_lines": message_lines,
            },
        )
        emit_payload(
            payload,
            run_dir=run_dir,
            base_dir=str(self.app_config.get("lobster_notify_dir", "runtime/lobster-notify")),
        )

    def _notify_dir(self, run_dir: Path) -> Path:
        """Retained for backwards-compatibility with any external caller
        that inspected the target directory. Delegates to the shared helper.
        """
        return payload_dir_for(
            run_dir,
            base=str(self.app_config.get("lobster_notify_dir", "runtime/lobster-notify")),
        )

    def _title_prefix(self) -> str:
        return str(self.app_config.get("feishu_title_prefix", "[XHS Cloud Login]")).strip() or "[XHS Cloud Login]"

    def _build_message_lines(self, screenshot_path: Path, *, run_dir: Path) -> list[str]:
        return [
            f"{self._title_prefix()} 小红书登录二维码",
            f"Run ID: {run_dir.name}",
            f"图片路径: {screenshot_path}",
            "请把这张二维码图片直接发到飞书群，用户扫码后等待任务继续。",
        ]
