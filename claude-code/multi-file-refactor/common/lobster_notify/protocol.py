"""Lobster notification payload protocol.

Contract: `xhs-auto-publisher` (producer) writes a JSON payload to
`runtime/lobster-notify/<run_id>/<kind>.payload.json`; OpenClaw Lobster
(consumer) reads it and forwards to the target IM channel (currently Feishu).

Producer doesn't hold any Feishu credentials — that lives in Lobster.
This module defines the stable shape of the payload; changing any of the
field names / structure below is a breaking change to the consumer.

Reference: docs/LOBSTER_NOTIFY_PROTOCOL.md (in xhs-auto-publisher).
"""
from __future__ import annotations

# Bump when payload shape changes in a way consumers must adapt to.
PROTOCOL_VERSION = "1.0"

CHANNEL_LOBSTER = "lobster_channel"

# `kind` — what event this payload represents.
KIND_LOGIN_QR = "login_qr"

# `action` — what the consumer should do with the payload.
ACTION_SEND_IMAGE_TO_FEISHU_GROUP = "send_image_to_feishu_group"

# `delivery.type` — the physical form of the attached artefact.
DELIVERY_TYPE_IMAGE_FILE = "image_file"

# Timezone offset for `ts`. Fixed to Asia/Shanghai (UTC+8) so producers
# on UTC CI runners and CST developer machines emit the same value.
FIXED_TZ_OFFSET_HOURS = 8
