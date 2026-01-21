from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VerificationResult:
    ok: bool
    status: str
    provider_event_id: str
    product_id: str
    response_hash: str | None = None
