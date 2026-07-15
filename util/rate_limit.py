"""Simple in-memory rate limiter for auth endpoints."""

from collections import defaultdict
from threading import Lock
from time import time

from flask import Request, jsonify


class RateLimiter:
    def __init__(self, max_attempts=10, window_seconds=60):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._hits = defaultdict(list)
        self._lock = Lock()

    def is_allowed(self, key: str) -> bool:
        now = time()
        with self._lock:
            hits = [t for t in self._hits[key] if now - t < self.window_seconds]
            if len(hits) >= self.max_attempts:
                self._hits[key] = hits
                return False
            hits.append(now)
            self._hits[key] = hits
            return True


# Shared limiters for login surfaces (per process; enough for single-instance deploys).
login_limiter = RateLimiter(max_attempts=10, window_seconds=60)
dashboard_login_limiter = RateLimiter(max_attempts=10, window_seconds=60)


def client_key(req: Request, suffix: str = "") -> str:
    forwarded = (req.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
    ip = forwarded or req.remote_addr or "unknown"
    return f"{ip}:{suffix}" if suffix else ip


def rate_limited_response():
    return jsonify({"message": "Too many attempts. Try again shortly."}), 429
