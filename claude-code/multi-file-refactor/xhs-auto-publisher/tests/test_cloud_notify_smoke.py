"""Smoke test — Lobster QR payload shape.

Guards the file contract in docs/LOBSTER_NOTIFY_PROTOCOL.md. Any breaking
change to the fields below is a breaking change for the Lobster consumer.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.cloud_notify import CloudNotifier


class LobsterPayloadSmokeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.run_dir = self.tmp / "runtime" / "runs" / "20260722-testrun"
        self.run_dir.mkdir(parents=True)
        self.screenshot = self.run_dir / "screenshots" / "login_qr.png"

    def _emit(self, extra_config: dict | None = None) -> dict:
        cfg = {"notify_qr_via": "lobster_channel"}
        if extra_config:
            cfg.update(extra_config)
        notifier = CloudNotifier(cfg)
        notifier.notify_qr(self.screenshot, run_dir=self.run_dir)
        payload_path = (
            self.tmp / "runtime" / "lobster-notify" / "20260722-testrun"
            / "login_qr.payload.json"
        )
        return json.loads(payload_path.read_text(encoding="utf-8"))

    def test_qr_handoff_enabled_gates_on_config(self) -> None:
        self.assertTrue(CloudNotifier({"notify_qr_via": "lobster_channel"}).qr_handoff_enabled())
        self.assertFalse(CloudNotifier({}).qr_handoff_enabled())
        self.assertFalse(CloudNotifier({"notify_qr_via": "none"}).qr_handoff_enabled())

    def test_payload_matches_protocol_shape(self) -> None:
        p = self._emit()
        # Fields the Lobster consumer relies on
        self.assertEqual(p["channel"], "lobster_channel")
        self.assertEqual(p["kind"], "login_qr")
        self.assertEqual(p["action"], "send_image_to_feishu_group")
        self.assertEqual(p["run_id"], "20260722-testrun")
        self.assertEqual(p["platform"], "xiaohongshu")
        self.assertEqual(p["delivery"]["type"], "image_file")
        self.assertEqual(p["delivery"]["path"], str(self.screenshot))
        self.assertEqual(p["delivery"]["caption_lines"], p["message_lines"])
        self.assertIn("Run ID: 20260722-testrun", p["message_lines"][1])

    def test_ts_uses_fixed_utc_plus_8(self) -> None:
        p = self._emit()
        # ISO 8601 with +08:00 offset — consistent across CI (UTC) and dev (CST).
        self.assertTrue(
            p["ts"].endswith("+08:00"),
            f"ts should be UTC+8, got: {p['ts']}",
        )

    def test_title_prefix_configurable(self) -> None:
        p = self._emit({"feishu_title_prefix": "[Prod]"})
        self.assertTrue(p["title"].startswith("[Prod]"), p["title"])

    def test_platform_defaults_to_xiaohongshu(self) -> None:
        p = self._emit()
        self.assertEqual(p["platform"], "xiaohongshu")

    def test_disabled_mode_rejects_call(self) -> None:
        notifier = CloudNotifier({"notify_qr_via": "none"})
        with self.assertRaises(RuntimeError):
            notifier.notify_qr(self.screenshot, run_dir=self.run_dir)


if __name__ == "__main__":
    unittest.main()
