import time

import pytest

from app.services.channel_rate_limiter import check_rate_limit, reset_rate_limits


@pytest.fixture(autouse=True)
def _reset():
    reset_rate_limits()
    yield
    reset_rate_limits()


class TestCheckRateLimit:
    def test_allows_requests_under_the_limit(self):
        for _ in range(3):
            assert check_rate_limit("+254712345678", max_requests=3, window_seconds=60) is True

    def test_blocks_requests_over_the_limit(self):
        for _ in range(3):
            check_rate_limit("+254712345678", max_requests=3, window_seconds=60)
        assert check_rate_limit("+254712345678", max_requests=3, window_seconds=60) is False

    def test_different_keys_have_independent_limits(self):
        for _ in range(3):
            check_rate_limit("+254712345678", max_requests=3, window_seconds=60)
        assert check_rate_limit("+254700000000", max_requests=3, window_seconds=60) is True

    def test_requests_outside_the_window_do_not_count(self):
        for _ in range(3):
            check_rate_limit("+254712345678", max_requests=3, window_seconds=0.05)
        time.sleep(0.1)
        assert check_rate_limit("+254712345678", max_requests=3, window_seconds=0.05) is True

    def test_reset_clears_all_limits(self):
        for _ in range(3):
            check_rate_limit("+254712345678", max_requests=3, window_seconds=60)
        reset_rate_limits()
        assert check_rate_limit("+254712345678", max_requests=3, window_seconds=60) is True
