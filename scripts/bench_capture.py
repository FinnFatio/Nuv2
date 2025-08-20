"""Benchmark helper for local capture latency.

Run this script to capture a fixed region multiple times and report p50/p95
latencies. This is a manual aid for performance tuning and is not part of the
automated test suite.
"""

import statistics
import time

from screenshot import capture


def main(samples: int = 50) -> None:
    region = (0, 0, 300, 120)
    times = []
    for _ in range(samples):
        start = time.perf_counter()
        img = capture(region)
        _ = img.size
        times.append((time.perf_counter() - start) * 1000)
    times.sort()
    p50 = statistics.quantiles(times, n=100)[49]
    p95 = statistics.quantiles(times, n=100)[94]
    print(f"n={samples} p50={p50:.2f}ms p95={p95:.2f}ms")


if __name__ == "__main__":  # pragma: no cover
    main()
