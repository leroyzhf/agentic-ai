"""Shared Feishu Open API client.

Public API — import from `feishu_client` directly:

    from feishu_client import (
        FeishuAPIError,
        get_tenant_access_token,
        open_api_request,
        list_tables, list_fields, list_records,
        batch_create_records, batch_update_records,
        upload_medium, choose_parent_type,
    )

Stdlib-only; safe to use from apps that promise no third-party dependencies.
"""
from .auth import (
    exchange_user_code,
    get_tenant_access_token,
    refresh_user_token,
)
from .bitable import (
    batch_create_records,
    batch_update_records,
    list_fields,
    list_records,
    list_tables,
)
from .drive import choose_parent_type, upload_medium
from .errors import FeishuAPIError
from .http import DEFAULT_ENDPOINT, open_api_request, post_multipart, post_json_no_auth

__all__ = [
    "DEFAULT_ENDPOINT",
    "FeishuAPIError",
    "batch_create_records",
    "batch_update_records",
    "choose_parent_type",
    "exchange_user_code",
    "get_tenant_access_token",
    "list_fields",
    "list_records",
    "list_tables",
    "open_api_request",
    "post_json_no_auth",
    "post_multipart",
    "refresh_user_token",
    "upload_medium",
]
