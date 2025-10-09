from __future__ import annotations

import time

"""Performance smoke test scaffold (QR-004, QR-005, QR-006).
Currently a placeholder verifying we can later plug timing logic.
"""


def test_perf_placeholder():
    start = time.perf_counter()
    # Simulate light work
    s = sum(i*i for i in range(50_000))
    assert s > 0
    elapsed = time.perf_counter() - start
    # Placeholder assertion: should run quickly (<< 1s) so CI stays fast
    assert elapsed < 1.5, f"perf placeholder too slow: {elapsed:.3f}s"
    # Provide derived metric example
    rows = 50_000
    throughput = rows / elapsed
    # Not asserting throughput yet; just ensuring math works
    assert throughput > 10_000  # extremely lenient placeholder
