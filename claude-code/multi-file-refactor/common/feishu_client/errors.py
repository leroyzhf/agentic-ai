from __future__ import annotations

from typing import Any


class FeishuAPIError(RuntimeError):
    """Raised for any failure from the Feishu Open API.

    Attributes:
        code: The `code` field from the Feishu response envelope, or -1 for
            transport-level failures (HTTP error, timeout, network unreachable).
        msg: The `msg`/`message` string from the response, or the transport
            error description.
        path: The API path (or full URL for transport failures) that produced
            the error, useful for logs.
        response_body: The parsed JSON body (or raw string for transport
            failures), preserved for callers that need to inspect it.
    """

    def __init__(
        self,
        code: int,
        msg: str,
        *,
        path: str = "",
        response_body: Any = None,
    ) -> None:
        self.code = code
        self.msg = msg
        self.path = path
        self.response_body = response_body
        super().__init__(f"Feishu API error code={code} path={path or '-'}: {msg}")
