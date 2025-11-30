import requests
import time
import threading
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Dict


def create_session(max_retries=3, backoff_factor=1.0, status_forcelist=(429, 500, 502, 503, 504), pool_size=10):
    s = requests.Session()
    retry = Retry(
        total=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=list(status_forcelist),
        allowed_methods=frozenset(["GET", "POST", "PUT", "DELETE", "PATCH"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=pool_size, pool_maxsize=pool_size)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s


class TokenBucket:
    def __init__(self, rate: float, capacity: float):
        self.rate = float(rate)
        self.capacity = float(capacity)
        self.tokens = float(capacity)
        self.timestamp = time.monotonic()
        self.lock = threading.Lock()

    def consume(self, tokens: float = 1.0, timeout: float = 1.0):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            with self.lock:
                now = time.monotonic()
                elapsed = now - self.timestamp
                self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
                self.timestamp = now
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return True
            time.sleep(0.01)
        return False


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.fail_count = 0
        self.open_until = 0.0
        self.lock = threading.Lock()

    def allow(self) -> bool:
        with self.lock:
            return time.monotonic() >= self.open_until

    def record_success(self):
        with self.lock:
            self.fail_count = 0
            self.open_until = 0.0

    def record_failure(self):
        with self.lock:
            self.fail_count += 1
            if self.fail_count >= self.failure_threshold:
                self.open_until = time.monotonic() + self.recovery_timeout


metrics: Dict[str, int] = {
    "api_requests_total": 0,
    "api_request_success": 0,
    "api_request_failures": 0,
    "api_request_latency_ms_sum": 0,
}


def update_metric(key: str, amount: int = 1):
    try:
        metrics[key] += amount
    except KeyError:
        metrics[key] = amount
