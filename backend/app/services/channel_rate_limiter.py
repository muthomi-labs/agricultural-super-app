import threading
import time

_lock = threading.Lock()
_hits = {}


def check_rate_limit(key, max_requests, window_seconds):
    now = time.monotonic()
    with _lock:
        timestamps = [t for t in _hits.get(key, []) if now - t < window_seconds]
        if len(timestamps) >= max_requests:
            _hits[key] = timestamps
            return False
        timestamps.append(now)
        _hits[key] = timestamps
        return True


def reset_rate_limits():
    with _lock:
        _hits.clear()
