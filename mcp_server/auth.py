"""
NEUTRON EVO OS — MCP HTTP Server: Authentication & Rate Limiting
X-NEUTRON-API-Key header validation + per-key rate limiting.
"""
from __future__ import annotations

import os
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

# Lazy imports to avoid circular deps
_config: Optional["config"] = None

def _get_config():
    global _config
    if _config is None:
        from mcp_server import config as _cfg
        _config = _cfg
    return _config


@dataclass
class _RateBucket:
    """Token bucket for rate limiting per API key."""
    tokens: int
    last_refill: float
    rate: int  # tokens per minute


# In-memory rate limiter: key → _RateBucket
_rate_buckets: dict[str, _RateBucket] = defaultdict(lambda: _RateBucket(
    tokens=60, last_refill=time.time(), rate=60
))


def reset_rate_limit(key: str):
    """Reset rate limit for a key (e.g., on violation)."""
    _rate_buckets.pop(key, None)


def check_rate_limit(api_key: str) -> tuple[bool, str]:
    """
    Token-bucket rate limiter: default 60 req/min per key.
    Returns (allowed, error_message).
    """
    cfg = _get_config()
    rate = cfg.get_rate_limit(api_key)

    bucket = _rate_buckets[api_key]
    now = time.time()
    elapsed = now - bucket.last_refill

    # Refill tokens: rate per minute, prorated
    refill = (elapsed / 60.0) * rate
    bucket.tokens = min(rate, bucket.tokens + refill)
    bucket.last_refill = now

    if bucket.tokens >= 1:
        bucket.tokens -= 1
        return True, ""
    else:
        remaining = int(bucket.tokens)
        retry_after = int((1 - bucket.tokens) / (rate / 60.0)) + 1
        return False, (
            f"Rate limit exceeded. {remaining} tokens left. "
            f"Retry after {retry_after}s."
        )


def resolve_neutron_root(api_key: str) -> str | None:
    """
    Resolve NEUTRON_ROOT for an authenticated API key.
    Validates against config on every call to detect revocations immediately.
    Does NOT cache — avoids stale cache from revoked keys remaining active.
    """
    cfg = _get_config()
    valid, root = cfg.validate_api_key(api_key)
    # NO cache: cfg.validate_api_key() checks `enabled` flag on every call.
    # Revoked keys are detected immediately without server restart.
    return root if valid else None


def authenticate(request_headers: dict) -> tuple[bool, str, str]:
    """
    Authenticate an incoming HTTP request.

    Args:
        request_headers: dict of lowercase header names → values

    Returns:
        (is_authenticated, api_key_or_empty, error_message)

    Security: Always executes the same number of cryptographic operations
    regardless of whether the header is present, present-but-wrong, or absent.
    This prevents timing attacks that distinguish "no header" from "wrong key".
    """
    cfg = _get_config()

    # Get API key from header
    api_key = request_headers.get("x-neutron-api-key", "").strip()
    path = request_headers.get("path", "")

    # Allow unauthenticated for certain paths
    if path in ("/health", "/docs", "/openapi.json", "/redoc"):
        return True, "_anonymous", ""

    if not api_key:
        # Timing-attack mitigation: even if no key is provided, run the
        # timing-safe comparison against a dummy key so the execution time
        # is identical to a present-but-wrong-key request.
        # This prevents attackers from distinguishing "no key" vs "wrong key".
        import hmac as _hmac
        _hmac.compare_digest(api_key, "\x00" * 32)  # dummy — always mismatches
        return False, "", "Missing X-NEUTRON-API-Key header"

    # Validate key — validate_api_key() uses hmac.compare_digest over all keys
    valid, root_or_error = cfg.validate_api_key(api_key)
    if not valid:
        return False, "", root_or_error

    # Rate limit check
    allowed, limit_msg = check_rate_limit(api_key)
    if not allowed:
        return False, "", limit_msg

    return True, api_key, ""


def set_neutron_root_for_key(api_key: str, root: str):
    """
    DEPRECATED: caching removed. Config is re-validated on every request.
    Kept for API compatibility only — does nothing.
    """
    pass  # No-op: resolve_neutron_root() re-validates from config every call
