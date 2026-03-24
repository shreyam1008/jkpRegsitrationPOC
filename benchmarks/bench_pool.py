"""Benchmark Suite 5: Database Connection Pool Stress Tests.

Tests the resilience and limits of the ThreadedConnectionPool(2-20):

  • Pool exhaustion — what happens when all 20 conns are busy?
  • Stale connection recovery — how fast does the pool replace dead conns?
  • Pool recreation — what happens when the entire pool is destroyed?
  • Concurrent pool access — thread safety under contention
  • Connection churn — rapid borrow/return cycles

These benchmarks use a custom mock pool that simulates real pool behavior
including blocking on exhaustion and connection failures.
"""

from __future__ import annotations

import contextlib
import random
import threading
import time
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any

from helpers import (
    BenchResult,
    Timer,
    _MockConnection,
    _MockCursor,
    logger,
    print_results,
    seed_mock_store,
)


# ---------------------------------------------------------------------------
# Simulated connection pool with realistic behavior
# ---------------------------------------------------------------------------


class SimulatedPool:
    """A mock pool that simulates ThreadedConnectionPool behavior.

    Features:
      - Configurable max connections
      - Blocks when pool is exhausted (like real psycopg2 pool)
      - Simulates connection failures at configurable rate
      - Tracks metrics: borrows, returns, waits, failures
    """

    def __init__(
        self,
        minconn: int = 2,
        maxconn: int = 20,
        conn_latency_ms: float = 0.0,
        failure_rate: float = 0.0,
        create_latency_ms: float = 0.0,
    ) -> None:
        self.maxconn = maxconn
        self.conn_latency_ms = conn_latency_ms
        self.failure_rate = failure_rate
        self.create_latency_ms = create_latency_ms

        self._semaphore = threading.Semaphore(maxconn)
        self._lock = threading.Lock()
        self._active = 0
        self._peak_active = 0
        self._total_borrows = 0
        self._total_waits = 0
        self._total_failures = 0
        self._total_wait_ms = 0.0
        self._created = 0

    @contextlib.contextmanager
    def get_conn(self) -> Generator[_MockConnection, None, None]:
        # Try to acquire, track wait time
        t0 = time.perf_counter()
        acquired = self._semaphore.acquire(timeout=10.0)
        wait_ms = (time.perf_counter() - t0) * 1000

        if not acquired:
            with self._lock:
                self._total_failures += 1
            raise TimeoutError("Pool exhausted — could not acquire connection in 10s")

        with self._lock:
            self._total_borrows += 1
            if wait_ms > 1.0:
                self._total_waits += 1
                self._total_wait_ms += wait_ms
            self._active += 1
            if self._active > self._peak_active:
                self._peak_active = self._active

        # Simulate connection creation time
        if self.create_latency_ms > 0:
            time.sleep(self.create_latency_ms / 1000)
            with self._lock:
                self._created += 1

        # Simulate random failure
        if self.failure_rate > 0 and random.random() < self.failure_rate:
            with self._lock:
                self._active -= 1
                self._total_failures += 1
            self._semaphore.release()
            raise ConnectionError("Simulated connection failure")

        try:
            yield _MockConnection(latency_ms=self.conn_latency_ms)
        finally:
            with self._lock:
                self._active -= 1
            self._semaphore.release()

    @property
    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "total_borrows": self._total_borrows,
                "peak_active": self._peak_active,
                "total_waits": self._total_waits,
                "avg_wait_ms": self._total_wait_ms / self._total_waits if self._total_waits > 0 else 0,
                "total_failures": self._total_failures,
                "maxconn": self.maxconn,
            }


# ---------------------------------------------------------------------------
# Suite A: Pool exhaustion — exceed maxconn
# ---------------------------------------------------------------------------


def _pool_worker(
    pool: SimulatedPool,
    n: int,
    hold_ms: float = 0.0,
) -> tuple[list[float], int]:
    """Worker that borrows a conn, optionally holds it, then returns it."""
    latencies = []
    errors = 0
    for _ in range(n):
        with Timer() as t:
            try:
                with pool.get_conn() as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT 1")
                    if hold_ms > 0:
                        time.sleep(hold_ms / 1000)
            except (TimeoutError, ConnectionError):
                errors += 1
        latencies.append(t.elapsed_ms)
    return latencies, errors


def bench_pool_exhaustion() -> list[BenchResult]:
    """Push more concurrent users than maxconn allows.

    Pool has 20 slots. With 10/20/30/50/100 concurrent workers each holding
    a connection for 10ms, we see queuing behavior emerge.
    """
    results = []
    for workers in [10, 20, 30, 50, 100]:
        pool = SimulatedPool(maxconn=20, conn_latency_ms=1.0)
        all_latencies: list[float] = []
        total_errors = 0
        requests_per_worker = 30

        t0 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(_pool_worker, pool, requests_per_worker, hold_ms=10.0)
                for _ in range(workers)
            ]
            for f in as_completed(futures):
                lats, errs = f.result()
                all_latencies.extend(lats)
                total_errors += errs
        duration = time.perf_counter() - t0

        total = workers * requests_per_worker
        result = BenchResult(
            f"Pool exhaust: {workers} workers (maxconn=20)",
            total, duration, all_latencies, total_errors,
        )
        result.extra.update(pool.stats)
        results.append(result)
        logger.info(
            "    %d workers → rps=%.1f, peak_active=%d, waits=%d, p99=%.2fms",
            workers, result.rps, pool.stats["peak_active"],
            pool.stats["total_waits"], result.p99,
        )

    return results


# ---------------------------------------------------------------------------
# Suite B: Connection hold time impact
# ---------------------------------------------------------------------------


def bench_hold_time_impact() -> list[BenchResult]:
    """How does connection hold time affect throughput?

    Longer queries = connections held longer = fewer available = more queuing.
    """
    results = []
    for hold_ms in [0, 1, 5, 10, 25, 50, 100]:
        pool = SimulatedPool(maxconn=20, conn_latency_ms=0.0)
        all_latencies: list[float] = []
        total_errors = 0
        workers = 50
        requests_per_worker = 20

        t0 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(_pool_worker, pool, requests_per_worker, hold_ms=float(hold_ms))
                for _ in range(workers)
            ]
            for f in as_completed(futures):
                lats, errs = f.result()
                all_latencies.extend(lats)
                total_errors += errs
        duration = time.perf_counter() - t0

        total = workers * requests_per_worker
        result = BenchResult(
            f"Hold time {hold_ms}ms (50 workers, pool=20)",
            total, duration, all_latencies, total_errors,
        )
        result.extra.update(pool.stats)
        result.extra["hold_ms"] = hold_ms
        results.append(result)
        logger.info(
            "    hold=%dms → rps=%.1f, peak=%d, waits=%d",
            hold_ms, result.rps, pool.stats["peak_active"], pool.stats["total_waits"],
        )

    return results


# ---------------------------------------------------------------------------
# Suite C: Connection failure resilience
# ---------------------------------------------------------------------------


def bench_connection_failures() -> list[BenchResult]:
    """Simulate connection failures at various rates.

    Real-world: DB restarts, network blips, connection timeouts.
    Tests the pool's ability to handle and recover from failures.
    """
    results = []
    for failure_rate in [0.0, 0.01, 0.05, 0.10, 0.25]:
        pool = SimulatedPool(maxconn=20, conn_latency_ms=2.0, failure_rate=failure_rate)
        all_latencies: list[float] = []
        total_errors = 0
        workers = 30
        requests_per_worker = 30

        t0 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(_pool_worker, pool, requests_per_worker, hold_ms=5.0)
                for _ in range(workers)
            ]
            for f in as_completed(futures):
                lats, errs = f.result()
                all_latencies.extend(lats)
                total_errors += errs
        duration = time.perf_counter() - t0

        total = workers * requests_per_worker
        result = BenchResult(
            f"Failure rate {failure_rate*100:.0f}% (30 workers)",
            total, duration, all_latencies, total_errors,
        )
        result.extra.update(pool.stats)
        result.extra["configured_failure_rate"] = failure_rate
        result.extra["actual_failure_rate"] = total_errors / total
        results.append(result)
        logger.info(
            "    fail_rate=%.0f%% → errors=%d/%d (%.1f%%), rps=%.1f",
            failure_rate * 100, total_errors, total, total_errors / total * 100, result.rps,
        )

    return results


# ---------------------------------------------------------------------------
# Suite D: Pool sizing experiment
# ---------------------------------------------------------------------------


def bench_pool_sizing() -> list[BenchResult]:
    """What pool size is optimal for 50 concurrent users?

    Tests: pool too small (2), default (20), generous (50), oversized (100).
    """
    results = []
    for maxconn in [2, 5, 10, 20, 50, 100]:
        pool = SimulatedPool(maxconn=maxconn, conn_latency_ms=2.0)
        all_latencies: list[float] = []
        total_errors = 0
        workers = 50
        requests_per_worker = 30

        t0 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(_pool_worker, pool, requests_per_worker, hold_ms=5.0)
                for _ in range(workers)
            ]
            for f in as_completed(futures):
                lats, errs = f.result()
                all_latencies.extend(lats)
                total_errors += errs
        duration = time.perf_counter() - t0

        total = workers * requests_per_worker
        result = BenchResult(
            f"Pool size={maxconn} (50 workers)",
            total, duration, all_latencies, total_errors,
        )
        result.extra.update(pool.stats)
        results.append(result)
        logger.info(
            "    pool=%d → rps=%.1f, peak=%d, waits=%d, p99=%.2fms",
            maxconn, result.rps, pool.stats["peak_active"], pool.stats["total_waits"], result.p99,
        )

    return results


# ---------------------------------------------------------------------------
# Suite E: Connection creation overhead
# ---------------------------------------------------------------------------


def bench_connection_creation_cost() -> list[BenchResult]:
    """Simulate the cost of creating new DB connections.

    In production, psycopg2 connection creation takes 5-50ms (TCP + auth).
    """
    results = []
    for create_ms in [0, 5, 10, 25, 50]:
        pool = SimulatedPool(maxconn=20, conn_latency_ms=2.0, create_latency_ms=float(create_ms))
        all_latencies: list[float] = []
        total_errors = 0
        workers = 30
        requests_per_worker = 20

        t0 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(_pool_worker, pool, requests_per_worker, hold_ms=5.0)
                for _ in range(workers)
            ]
            for f in as_completed(futures):
                lats, errs = f.result()
                all_latencies.extend(lats)
                total_errors += errs
        duration = time.perf_counter() - t0

        total = workers * requests_per_worker
        result = BenchResult(
            f"Conn create cost={create_ms}ms",
            total, duration, all_latencies, total_errors,
        )
        result.extra.update(pool.stats)
        results.append(result)
        logger.info("    create=%dms → rps=%.1f, p99=%.2fms", create_ms, result.rps, result.p99)

    return results


# ---------------------------------------------------------------------------
# Suite F: Rapid borrow/return churn
# ---------------------------------------------------------------------------


def bench_churn(n: int = 5000) -> BenchResult:
    """Rapid-fire borrow/return — tests pool lock contention."""
    pool = SimulatedPool(maxconn=20, conn_latency_ms=0.0)
    latencies: list[float] = []
    errors = 0

    t0 = time.perf_counter()
    for _ in range(n):
        with Timer() as t:
            try:
                with pool.get_conn() as conn:
                    pass  # immediate return
            except Exception:
                errors += 1
        latencies.append(t.elapsed_ms)
    duration = time.perf_counter() - t0

    result = BenchResult("Pool churn (rapid borrow/return)", n, duration, latencies, errors)
    result.extra.update(pool.stats)
    return result


def bench_churn_concurrent() -> BenchResult:
    """Concurrent churn — 100 threads doing rapid borrow/return."""
    pool = SimulatedPool(maxconn=20, conn_latency_ms=0.0)
    all_latencies: list[float] = []
    total_errors = 0
    workers = 100
    requests_per_worker = 100

    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(_pool_worker, pool, requests_per_worker, hold_ms=0.0)
            for _ in range(workers)
        ]
        for f in as_completed(futures):
            lats, errs = f.result()
            all_latencies.extend(lats)
            total_errors += errs
    duration = time.perf_counter() - t0

    total = workers * requests_per_worker
    result = BenchResult("Pool churn concurrent (100 threads)", total, duration, all_latencies, total_errors)
    result.extra.update(pool.stats)
    return result


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def run_all() -> list[BenchResult]:
    """Run all connection pool benchmarks."""
    logger.info("Starting connection pool stress tests...")

    results: list[BenchResult] = []

    logger.info("  [1/6] Pool exhaustion (10→100 workers, maxconn=20)...")
    results.extend(bench_pool_exhaustion())

    logger.info("  [2/6] Connection hold time impact...")
    results.extend(bench_hold_time_impact())

    logger.info("  [3/6] Connection failure resilience...")
    results.extend(bench_connection_failures())

    logger.info("  [4/6] Pool sizing experiment...")
    results.extend(bench_pool_sizing())

    logger.info("  [5/6] Connection creation overhead...")
    results.extend(bench_connection_creation_cost())

    logger.info("  [6/6] Rapid churn tests...")
    results.append(bench_churn())
    results.append(bench_churn_concurrent())

    print_results(results, "Database Connection Pool Stress Tests")
    return results


if __name__ == "__main__":
    run_all()
