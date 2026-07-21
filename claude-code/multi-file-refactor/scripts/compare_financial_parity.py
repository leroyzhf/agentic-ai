#!/usr/bin/env python3
"""Compare Feishu HTTP requests: old sync_bitable vs new code.

Usage:
    cd financial-automation
    python ../scripts/compare_financial_parity.py
"""
import copy
import io
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
SCRIPT_DIR = ROOT / "scripts"
sys.path.insert(0, str(ROOT))

# Patch BEFORE importing anything else
stub_resp = json.dumps({"code": 0, "msg": "stub", "data": {}}).encode("utf-8")
RECORDED = []

def record(req, *a, **kw):
    RECORDED.append({
        "method": req.method,
        "url": req.full_url,
        "body": json.loads(req.data) if req.data else None,
    })
    import http.client
    return io.BytesIO(stub_resp)


with patch("urllib.request.urlopen", record):
    # Import old code copy from scripts/
    import importlib.util
    spec = importlib.util.spec_from_file_location("old_sb", str(SCRIPT_DIR / "old_sync_bitable.py"))
    old_sb = importlib.util.module_from_spec(spec)
    # Bypass the KW_ONLY dataclass issue by injecting __file__ and __package__
    spec.loader.exec_module(old_sb)

    s = old_sb.BitableSettings(
        enabled=True, dry_run=False, endpoint="https://open.feishu.cn",
        batch_size=200, mode="app_identity", include_attachments=False,
        app_id="test_api", app_secret="test_secret",
        app_token="test_token",
        transport_table_id="tbl_t", expense_table_id="tbl_e",
    )
    t = old_sb.get_tenant_access_token(s)
    old_sb.batch_create_records(settings=s, access_token=t, table_id="tbl_t",
                                 records=[{"fields": {"金额": 520.0}}])

old_entries = list(RECORDED)

# New code
RECORDED.clear()
with patch("urllib.request.urlopen", record):
    from feishu_client import get_tenant_access_token as new_token
    from feishu_client import batch_create_records as new_batch
    t2 = new_token("test_api", "test_secret", endpoint="https://open.feishu.cn")
    new_batch("test_token", "tbl_t", [{"fields": {"金额": 520.0}}], t2, endpoint="https://open.feishu.cn")

new_entries = list(RECORDED)

# Strip host for comparison
def strip(entries):
    out = []
    for e in entries:
        url = e["url"]
        if "/open-apis/" in url:
            url = "/open-apis/" + url.rsplit("/open-apis/", 1)[-1]
        out.append({"method": e["method"], "url": url, "body": e["body"]})
    return out

o = strip(old_entries)
n = strip(new_entries)

if o == n:
    print(f"[PASS] financial: {len(o)} request(s), all match")
    # Show recorded for transparency
    for e in old_entries:
        body_short = json.dumps(e["body"], ensure_ascii=False)[:200]
        print(f"  {e['method']} {e['url']}  body={body_short}")
else:
    import difflib
    old_text = json.dumps(o, indent=2, ensure_ascii=False)
    new_text = json.dumps(n, indent=2, ensure_ascii=False)
    for line in difflib.unified_diff(old_text.splitlines(), new_text.splitlines(),
                                     fromfile="old", tofile="new", lineterm=""):
        print(line)
    sys.exit(1)
