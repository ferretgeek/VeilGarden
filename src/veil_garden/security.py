from __future__ import annotations

import re
import secrets
import threading
import time
from collections import defaultdict, deque
from urllib.parse import urlsplit

EMAIL_RE = re.compile(r"^[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Z0-9](?:[A-Z0-9.-]{0,251}[A-Z0-9])?$", re.I)
CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
TAG_RE = re.compile(r"^[\w\-\u4e00-\u9fff ]+$", re.UNICODE)


def clean_text(value: object, *, limit: int) -> str:
    text = CONTROL_RE.sub("", str(value or "")).strip()
    return text[:limit]


def normalize_email(value: object) -> str:
    email = clean_text(value, limit=320).lower()
    if not EMAIL_RE.fullmatch(email) or ".." in email:
        raise ValueError("invalid email address")
    local, domain = email.rsplit("@", 1)
    if len(local) > 64 or len(domain) > 255 or "." not in domain:
        raise ValueError("invalid email address")
    return email


def clean_tags(value: object) -> list[str]:
    if isinstance(value, str):
        raw = value.split(",")
    elif isinstance(value, list):
        raw = value
    else:
        raw = []
    tags: list[str] = []
    for item in raw:
        tag = clean_text(item, limit=128)
        if len(tag) > 24:
            continue
        if tag and TAG_RE.fullmatch(tag) and tag.casefold() not in {x.casefold() for x in tags}:
            tags.append(tag)
        if len(tags) == 8:
            break
    return tags


def mask_email(email: str) -> str:
    local, domain = email.rsplit("@", 1)
    domain_parts = domain.split(".")
    visible_local = local[:1] if local else "•"
    domain_head = domain_parts[0][:1] if domain_parts[0] else "•"
    suffix = domain_parts[-1] if len(domain_parts) > 1 else ""
    masked_domain = f"{domain_head}{'•' * 4}"
    if suffix:
        masked_domain += f".{suffix}"
    return f"{visible_local}{'•' * 5}@{masked_domain}"


def bearer_matches(header: str | None, expected: str) -> bool:
    if not header or not header.startswith("Bearer "):
        return False
    return secrets.compare_digest(header[7:], expected)


def host_allowed(host_header: str | None, allowed: frozenset[str]) -> bool:
    if not host_header:
        return False
    candidate = host_header.strip().lower().rstrip(".")
    if candidate.startswith("["):
        end = candidate.find("]")
        hostname = candidate[1:end] if end > 0 else ""
    else:
        hostname = candidate.rsplit(":", 1)[0] if candidate.count(":") == 1 else candidate
    return hostname in allowed


def same_origin(origin: str | None, host_header: str | None) -> bool:
    if not origin:
        return True
    if not host_header:
        return False
    try:
        parsed = urlsplit(origin)
    except ValueError:
        return False
    origin_authority = parsed.netloc.lower().rstrip(".")
    request_authority = host_header.lower().rstrip(".")
    return parsed.scheme in {"http", "https"} and origin_authority == request_authority


class SlidingWindowLimiter:
    def __init__(self, *, limit: int, window_seconds: float) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] < cutoff:
                hits.popleft()
            if len(hits) >= self.limit:
                return False
            hits.append(now)
            return True
