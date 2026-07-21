"""Feishu authentication token acquisition.

Provides tenant token (app_id/app_secret) and user OAuth token flows.
Persistence (writing tokens to disk) is the CLI shell's job — this module
only speaks HTTP.
"""
from __future__ import annotations

from typing import Any

from .errors import FeishuAPIError
from .http import DEFAULT_ENDPOINT, DEFAULT_TIMEOUT, post_json_no_auth


def get_tenant_access_token(
    app_id: str,
    app_secret: str,
    *,
    endpoint: str = DEFAULT_ENDPOINT,
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    """Exchange app credentials for a `tenant_access_token`."""
    if not app_id or not app_secret:
        raise FeishuAPIError(
            code=-1,
            msg="Missing app_id or app_secret.",
            path="/open-apis/auth/v3/tenant_access_token/internal",
        )
    resp = post_json_no_auth(
        "/open-apis/auth/v3/tenant_access_token/internal",
        {"app_id": app_id, "app_secret": app_secret},
        endpoint=endpoint,
        timeout=timeout,
    )
    token = str(resp.get("tenant_access_token") or "")
    if not token:
        raise FeishuAPIError(
            code=int(resp.get("code", 0) or 0),
            msg="Response did not contain tenant_access_token.",
            path="/open-apis/auth/v3/tenant_access_token/internal",
            response_body=resp,
        )
    return token


def exchange_user_code(
    app_id: str,
    app_secret: str,
    code: str,
    *,
    endpoint: str = DEFAULT_ENDPOINT,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Exchange an OAuth authorization code for a user access token payload."""
    return post_json_no_auth(
        "/open-apis/authen/v1/access_token",
        {
            "grant_type": "authorization_code",
            "code": code,
            "app_id": app_id,
            "app_secret": app_secret,
        },
        endpoint=endpoint,
        timeout=timeout,
    )


def refresh_user_token(
    app_id: str,
    app_secret: str,
    refresh_token: str,
    *,
    endpoint: str = DEFAULT_ENDPOINT,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Refresh a user access token using a stored refresh token."""
    return post_json_no_auth(
        "/open-apis/authen/v1/refresh_access_token",
        {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "app_id": app_id,
            "app_secret": app_secret,
        },
        endpoint=endpoint,
        timeout=timeout,
    )
