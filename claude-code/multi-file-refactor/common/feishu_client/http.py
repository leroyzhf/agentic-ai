"""Low-level HTTP transport for the Feishu Open API.

Stdlib-only (uses `urllib`). Provides:
- `open_api_request` for JSON endpoints (with bearer token, envelope check,
  and opt-in retries for idempotent verbs).
- `post_multipart` for the medias/upload_all path — writing methods do NOT
  auto-retry (non-idempotent).

Callers should catch `FeishuAPIError` and re-raise app-specific types.
"""
from __future__ import annotations

import json
import time
import uuid
from typing import Any
from urllib import error, parse, request

from .errors import FeishuAPIError


DEFAULT_ENDPOINT = "https://open.feishu.cn"
DEFAULT_TIMEOUT = 60
_SAFE_METHODS = {"GET", "HEAD"}


def open_api_request(
    path: str,
    *,
    token: str,
    method: str = "GET",
    query: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None,
    endpoint: str = DEFAULT_ENDPOINT,
    timeout: int = DEFAULT_TIMEOUT,
    retries: int | None = None,
) -> dict[str, Any]:
    """Call a Feishu Open API JSON endpoint.

    `path` starts with `/` (e.g. `/open-apis/bitable/v1/apps/...`).
    `endpoint` should NOT have a trailing slash.

    Retries: `None` means "auto — GET/HEAD retry up to 2 times, others 0".
    Explicit `retries=0` disables retries even for GET.
    """
    method_upper = method.upper()
    if retries is None:
        retries = 2 if method_upper in _SAFE_METHODS else 0

    url = _build_url(endpoint, path, query)
    payload = None if body is None else json.dumps(body).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }
    req = request.Request(url, data=payload, headers=headers, method=method_upper)
    return _read_json_with_retry(req, path=path, retries=retries, timeout=timeout)


def post_multipart(
    path: str,
    *,
    token: str,
    fields: dict[str, str],
    file_field_name: str,
    file_name: str,
    file_bytes: bytes,
    content_type: str,
    endpoint: str = DEFAULT_ENDPOINT,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """POST a multipart/form-data body. No retry (upload is non-idempotent)."""
    boundary = f"----FeishuClientBoundary{uuid.uuid4().hex}"
    body = bytearray()

    for key, value in fields.items():
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(
            f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode("utf-8")
        )
        body.extend(str(value).encode("utf-8"))
        body.extend(b"\r\n")

    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(
        (
            f'Content-Disposition: form-data; name="{file_field_name}"; '
            f'filename="{file_name}"\r\n'
        ).encode("utf-8")
    )
    body.extend(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
    body.extend(file_bytes)
    body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode("utf-8"))

    url = _build_url(endpoint, path, query=None)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    }
    req = request.Request(url, data=bytes(body), headers=headers, method="POST")
    return _read_json_with_retry(req, path=path, retries=0, timeout=timeout)


def post_json_no_auth(
    path: str,
    payload: dict[str, Any],
    *,
    endpoint: str = DEFAULT_ENDPOINT,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """POST a JSON body WITHOUT an Authorization header. Used by auth endpoints
    (they take app_id/app_secret in the body, not a bearer token)."""
    url = _build_url(endpoint, path, query=None)
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    # Token acquisition IS retryable — the request is idempotent on the server.
    return _read_json_with_retry(req, path=path, retries=2, timeout=timeout)


def _build_url(endpoint: str, path: str, query: dict[str, Any] | None) -> str:
    base = endpoint.rstrip("/")
    if not path.startswith("/"):
        path = "/" + path
    url = base + path
    if query:
        clean = {k: v for k, v in query.items() if v is not None}
        if clean:
            url = url + "?" + parse.urlencode(clean, doseq=True)
    return url


def _read_json_with_retry(
    req: request.Request,
    *,
    path: str,
    retries: int,
    timeout: int,
) -> dict[str, Any]:
    attempt = 0
    while True:
        try:
            with request.urlopen(req, timeout=timeout) as resp:
                raw_body = resp.read().decode("utf-8")
        except error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            if _should_retry_http(exc.code) and attempt < retries:
                attempt += 1
                time.sleep(_backoff(attempt))
                continue
            raise FeishuAPIError(
                code=exc.code,
                msg=f"HTTP {exc.code}: {raw}",
                path=path,
                response_body=raw,
            ) from exc
        except error.URLError as exc:
            if attempt < retries:
                attempt += 1
                time.sleep(_backoff(attempt))
                continue
            raise FeishuAPIError(
                code=-1,
                msg=f"transport failure: {exc}",
                path=path,
                response_body=None,
            ) from exc

        payload = json.loads(raw_body or "{}")
        code = int(payload.get("code", 0) or 0)
        if code == 0:
            return payload
        # 429 / 5xx envelope-level codes could be retried, but the semantics
        # vary by endpoint — we do NOT retry on non-zero envelope codes to
        # avoid duplicate writes on non-idempotent verbs.
        raise FeishuAPIError(
            code=code,
            msg=str(payload.get("msg") or payload.get("message") or "unknown"),
            path=path,
            response_body=payload,
        )


def _should_retry_http(status: int) -> bool:
    return status == 429 or 500 <= status < 600


def _backoff(attempt: int) -> float:
    # Simple linear backoff: 0.5s, 1.0s, 1.5s ...
    return 0.5 * attempt
