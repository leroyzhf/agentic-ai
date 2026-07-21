#!/usr/bin/env python3
"""Verify that old and new Feishu code produce identical HTTP requests.

Patches urllib.request.urlopen to record every request (method, url, body),
then runs the same scenario with old and new code paths side-by-side.

Usage:
    cd ~/projects/agentic-ai/claude-code/multi-file-refactor
    ./scripts/verify_feishu_parity.py

Exit 0 = all requests match; non-zero = diff printed.
"""
from __future__ import annotations

import io
import json
import os
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent  # workspace root (~/.../multi-file-refactor)
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "financial-automation"))

RECORDED: list[dict[str, Any]] = []


def _record_urlopen(req, *a, **kw):
    body_raw = req.data
    body_str = body_raw.decode("utf-8") if body_raw else None
    parsed: dict | None = json.loads(body_str) if body_str else None
    RECORDED.append({
        "method": req.method or "GET",
        "url": req.full_url or req.selector,
        "body": parsed,
    })
    stub = json.dumps({"code": 0, "msg": "stub", "data": {}}).encode("utf-8")
    return io.BytesIO(stub)


def normalize(entries: list[dict]) -> list[dict]:
    """Strip host so old (`https://open.feishu.cn/path`) vs new match."""
    out = []
    for e in entries:
        url = e["url"]
        base = url.rstrip("/")
        if "/open-apis/" in base:
            url = base.rsplit("/open-apis/", 1)[-1]
            url = "/open-apis/" + url
        out.append({"method": e["method"], "url": url, "body": e["body"]})
    return out


# ── Financial-automation: old vs new ────────────────────────────────


def _import_old_sync_bitable():
    """Load old sync_bitable module directly from scripts/."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "old_sync_bitable",
        str(ROOT / "scripts" / "old_sync_bitable.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _import_old_crm():
    spec = importlib.util.spec_from_file_location(
        "old_crm_assistant",
        str(ROOT / "scripts" / "old_crm_assistant.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_financial_old():
    old = _import_old_sync_bitable()
    settings = old.BitableSettings(
        enabled=True, dry_run=False, endpoint="https://open.feishu.cn",
        batch_size=200, mode="app_identity", include_attachments=False,
        app_id="test_app_id", app_secret="test_app_secret",
        app_token="test_app_token",
        transport_table_id="tbl_transport", expense_table_id="tbl_expense",
    )
    token = old.get_tenant_access_token(settings)
    old.batch_create_records(
        settings=settings, access_token=token,
        table_id="tbl_transport",
        records=[{"fields": {"doc_id": "doc-1", "金额": 520.0}}],
    )


def run_financial_new():
    from financial_automation.src.sync_bitable import BitableSettings
    from feishu_client import get_tenant_access_token, batch_create_records

    settings = BitableSettings(
        enabled=True, dry_run=False, endpoint="https://open.feishu.cn",
        batch_size=200, mode="app_identity", include_attachments=False,
        app_id="test_app_id", app_secret="test_app_secret",
        app_token="test_app_token",
        transport_table_id="tbl_transport", expense_table_id="tbl_expense",
    )
    token = get_tenant_access_token(settings.app_id, settings.app_secret, endpoint=settings.endpoint)
    batch_create_records(
        settings.app_token, "tbl_transport",
        [{"fields": {"doc_id": "doc-1", "金额": 520.0}}],
        token, endpoint=settings.endpoint,
    )


# ── CRM: old vs new ─────────────────────────────────────────────────


def _crm_packet() -> dict:
    return {
        "customer_row": {"客户ID": "CUST-001", "客户名称": "T", "客户公司": "C", "来源渠道": "M"},
        "customer_rows": [{"客户ID": "CUST-001", "客户名称": "T", "客户公司": "C"}],
        "opportunity_row": {"商机ID": "OPP-001", "机会名称": "O", "当前阶段": "需求确认", "客户公司": "C"},
        "meeting_row": {"meeting_uuid": "m-001", "title": "MtG"},
        "customer_context": {"company_name": "C", "industry": "AI"},
        "follow_up_task": {},
    }


def run_crm_old():
    old = _import_old_crm()
    old.sync_crm_packet_to_feishu(
        _crm_packet(), "/tmp/crm_old_out",
        app_id="test_app_id", app_secret="test_app_secret",
        app_token_or_url="test_app_token",
        customer_table_id="tbl_customer",
        opportunity_table_id="tbl_opportunity",
        dry_run=False,
    )


def run_crm_new():
    from CRM_Assistant.scripts.crm_assistant import sync_crm_packet_to_feishu
    sync_crm_packet_to_feishu(
        _crm_packet(), "/tmp/crm_new_out",
        app_id="test_app_id", app_secret="test_app_secret",
        app_token_or_url="test_app_token",
        customer_table_id="tbl_customer",
        opportunity_table_id="tbl_opportunity",
        dry_run=False,
    )


# ── Main ─────────────────────────────────────────────────────────────


IMPORTS = {
    "financial_automation": str(ROOT / "financial-automation"),
    "CRM_Assistant": str(ROOT / "CRM-Assistant"),
    "scripts": str(ROOT / "scripts"),
}
for p in IMPORTS.values():
    if p not in sys.path:
        sys.path.insert(0, p)


CASES = [
    ("financial-auth+create", run_financial_old, run_financial_new),
    ("crm-full-pipeline", run_crm_old, run_crm_new),
]

failures = 0
for label, old_fn, new_fn in CASES:
    RECORDED.clear()
    with patch("urllib.request.urlopen", _record_urlopen):
        old_fn()
    old_entries = normalize(list(RECORDED))

    RECORDED.clear()
    with patch("urllib.request.urlopen", _record_urlopen):
        new_fn()
    new_entries = normalize(list(RECORDED))

    if old_entries == new_entries:
        print(f"[PASS] {label}: {len(old_entries)} request(s), all match")
    else:
        print(f"[FAIL] {label}")
        import difflib
        old_text = json.dumps(old_entries, indent=2, ensure_ascii=False)
        new_text = json.dumps(new_entries, indent=2, ensure_ascii=False)
        for line in difflib.unified_diff(
            old_text.splitlines(), new_text.splitlines(),
            fromfile=f"{label}-old", tofile=f"{label}-new",
            lineterm="",
        ):
            print(line)
        failures += 1

if failures:
    print(f"\n❌ {failures} case(s) differ — Feishu behaviour changed!")
    raise SystemExit(1)
else:
    print(f"\n✅ All {len(CASES)} case(s) pass — Feishu requests identical, behaviour preserved.")
