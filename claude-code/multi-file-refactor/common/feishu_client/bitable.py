"""Feishu Bitable REST helpers.

All list_* functions transparently paginate. All batch_* functions chunk
records. Business logic (record-field mapping, upsert decisions, field-type
coercion) stays in the calling app.
"""
from __future__ import annotations

from typing import Any

from .http import DEFAULT_ENDPOINT, DEFAULT_TIMEOUT, open_api_request


_MAX_PAGE_SIZE = 500
_DEFAULT_BATCH_SIZE = 500


def list_tables(
    app_token: str,
    token: str,
    *,
    endpoint: str = DEFAULT_ENDPOINT,
    timeout: int = DEFAULT_TIMEOUT,
    page_size: int = 100,
) -> list[dict[str, Any]]:
    path = f"/open-apis/bitable/v1/apps/{app_token}/tables"
    return _paginate_get(path, token, endpoint=endpoint, timeout=timeout, page_size=page_size)


def list_fields(
    app_token: str,
    table_id: str,
    token: str,
    *,
    endpoint: str = DEFAULT_ENDPOINT,
    timeout: int = DEFAULT_TIMEOUT,
    page_size: int = 500,
) -> list[dict[str, Any]]:
    path = f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields"
    return _paginate_get(path, token, endpoint=endpoint, timeout=timeout, page_size=page_size)


def list_records(
    app_token: str,
    table_id: str,
    token: str,
    *,
    endpoint: str = DEFAULT_ENDPOINT,
    timeout: int = DEFAULT_TIMEOUT,
    page_size: int = _MAX_PAGE_SIZE,
) -> list[dict[str, Any]]:
    path = f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records"
    return _paginate_get(path, token, endpoint=endpoint, timeout=timeout, page_size=page_size)


def batch_create_records(
    app_token: str,
    table_id: str,
    records: list[dict[str, Any]],
    token: str,
    *,
    endpoint: str = DEFAULT_ENDPOINT,
    timeout: int = DEFAULT_TIMEOUT,
    batch_size: int = _DEFAULT_BATCH_SIZE,
) -> list[dict[str, Any]]:
    """Batch-create records; returns the concatenated list of created records
    (each item is the raw Feishu record object as returned by the API)."""
    path = f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create"
    return _batch_write(
        path, records, token, endpoint=endpoint, timeout=timeout, batch_size=batch_size
    )


def batch_update_records(
    app_token: str,
    table_id: str,
    records: list[dict[str, Any]],
    token: str,
    *,
    endpoint: str = DEFAULT_ENDPOINT,
    timeout: int = DEFAULT_TIMEOUT,
    batch_size: int = _DEFAULT_BATCH_SIZE,
) -> list[dict[str, Any]]:
    """Batch-update records; each record dict must include `record_id`."""
    path = f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_update"
    return _batch_write(
        path, records, token, endpoint=endpoint, timeout=timeout, batch_size=batch_size
    )


def _paginate_get(
    path: str,
    token: str,
    *,
    endpoint: str,
    timeout: int,
    page_size: int,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    page_token: str | None = None
    while True:
        query: dict[str, Any] = {"page_size": page_size}
        if page_token:
            query["page_token"] = page_token
        resp = open_api_request(
            path,
            token=token,
            method="GET",
            query=query,
            endpoint=endpoint,
            timeout=timeout,
        )
        data = resp.get("data") or {}
        items.extend(data.get("items") or [])
        page_token = data.get("page_token") or None
        if not data.get("has_more") or not page_token:
            break
    return items


def _batch_write(
    path: str,
    records: list[dict[str, Any]],
    token: str,
    *,
    endpoint: str,
    timeout: int,
    batch_size: int,
) -> list[dict[str, Any]]:
    written: list[dict[str, Any]] = []
    step = max(1, min(batch_size, _MAX_PAGE_SIZE))
    for offset in range(0, len(records), step):
        chunk = records[offset : offset + step]
        resp = open_api_request(
            path,
            token=token,
            method="POST",
            body={"records": chunk},
            endpoint=endpoint,
            timeout=timeout,
            # batch_create/batch_update are non-idempotent — no auto-retry.
            retries=0,
        )
        data = resp.get("data") or {}
        chunk_written = data.get("records") if isinstance(data, dict) else None
        if isinstance(chunk_written, list):
            written.extend(chunk_written)
        else:
            # Server accepted but didn't echo records — record the intent
            # anyway so len(written) is a stable count.
            written.extend([{} for _ in chunk])
    return written
