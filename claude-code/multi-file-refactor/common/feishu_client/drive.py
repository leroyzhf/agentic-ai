"""Feishu Drive media upload — the shared path Bitable attachments use.

`token` may be either a tenant_access_token or a user_access_token; the caller
decides based on which parent_type they're targeting. This module does not
enforce a specific auth mode.
"""
from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Any

from .errors import FeishuAPIError
from .http import DEFAULT_ENDPOINT, post_multipart


_MEDIA_UPLOAD_PATH = "/open-apis/drive/v1/medias/upload_all"
_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}


def upload_medium(
    *,
    file_path: str | Path,
    parent_type: str,
    parent_node: str,
    token: str,
    endpoint: str = DEFAULT_ENDPOINT,
    timeout: int = 120,
) -> dict[str, Any]:
    """Upload a file to Feishu Drive as a Bitable/doc medium.

    Returns a dict containing `file_token`, `file_name`, `parent_type`,
    `mime_type`, `size`, plus the raw `path` for logging convenience.
    """
    path = Path(file_path)
    if not path.exists():
        raise FeishuAPIError(
            code=-1,
            msg=f"Attachment file does not exist: {path}",
            path=_MEDIA_UPLOAD_PATH,
        )

    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    resp = post_multipart(
        _MEDIA_UPLOAD_PATH,
        token=token,
        fields={
            "file_name": path.name,
            "parent_type": parent_type,
            "parent_node": parent_node,
            "size": str(path.stat().st_size),
        },
        file_field_name="file",
        file_name=path.name,
        file_bytes=path.read_bytes(),
        content_type=mime_type,
        endpoint=endpoint,
        timeout=timeout,
    )
    data = resp.get("data") if isinstance(resp, dict) else None
    file_token = str((data or {}).get("file_token") or "")
    if not file_token:
        raise FeishuAPIError(
            code=int(resp.get("code", 0) or 0) if isinstance(resp, dict) else -1,
            msg=f"Feishu did not return file_token for {path.name}.",
            path=_MEDIA_UPLOAD_PATH,
            response_body=resp,
        )
    return {
        "path": str(path),
        "file_name": path.name,
        "file_token": file_token,
        "parent_type": parent_type,
        "mime_type": mime_type,
        "size": path.stat().st_size,
    }


def choose_parent_type(path: str | Path) -> str:
    """Pick the Bitable attachment parent_type based on file extension.

    Bitable treats image formats specially (thumbnail rendering), so we
    return `bitable_image` for common raster formats and `bitable_file` for
    everything else.
    """
    suffix = Path(path).suffix.lower()
    return "bitable_image" if suffix in _IMAGE_SUFFIXES else "bitable_file"
