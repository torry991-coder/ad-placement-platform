#!/usr/bin/env python3
"""
Load testing script for 100K concurrent users.

Uses asyncio + httpx for concurrent async requests.
Tests: health check, auth, campaign CRUD, bidding auction, analytics dashboard.

Usage:
    python loadtest.py --url http://localhost:8000 --concurrency 1000 --duration 60
"""

from __future__ import annotations

import argparse
import asyncio
import time
import sys
from dataclasses import dataclass, field

try:
    import httpx
except ImportError:
    print("Please install httpx: pip install httpx")
    sys.exit(1)


@dataclass
class Stats:
    total: int = 0
    success: int = 0
    errors: int = 0
    latencies: list[float] = field(default_factory=list)
    status_codes: dict[int, int] = field(default_factory=dict)

    def record(self, latency: float, status: int) -> None:
        self.total += 1
        if 200 <= status < 400:
            self.success += 1
        else:
            self.errors += 1
        self.latencies.append(latency)
        self.status_codes[status] = self.status_codes.get(status, 0) + 1

    def summary(self) -> str:
        if not self.latencies:
            return "No requests completed"
        lat = sorted(self.latencies)
        n = len(lat)
        return (
            f"Requests: {self.total} | Success: {self.success} | Errors: {self.errors}\n"
            f"Latency (ms): p50={lat[n//2]*1000:.1f} p95={lat[int(n*0.95)]*1000:.1f} "
            f"p99={lat[int(n*0.99)]*1000:.1f} max={max(lat)*1000:.1f}\n"
            f"Throughput: {self.total / max(lat[-1] - lat[0], 0.001):.1f} req/s\n"
            f"Status codes: {dict(self.status_codes)}"
        )


class LoadTester:
    def __init__(self, base_url: str, concurrency: int, token: str = ""):
        self.base_url = base_url.rstrip("/")
        self.concurrency = concurrency
        self.token = token
        self.stats = Stats()
        self.semaphore = asyncio.Semaphore(concurrency)

    async def _request(self, client: httpx.AsyncClient, method: str, path: str, **kwargs) -> None:
        async with self.semaphore:
            t0 = time.time()
            try:
                resp = await client.request(method, f"{self.base_url}{path}", **kwargs)
                elapsed = time.time() - t0
                self.stats.record(elapsed, resp.status_code)
            except Exception:
                elapsed = time.time() - t0
                self.stats.record(elapsed, 0)

    async def _health_check_worker(self, client: httpx.AsyncClient) -> None:
        while True:
            await self._request(client, "GET", "/api/health")

    async def _campaign_list_worker(self, client: httpx.AsyncClient) -> None:
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        while True:
            await self._request(client, "GET", "/api/campaigns/", headers=headers)

    async def _auction_worker(self, client: httpx.AsyncClient) -> None:
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        payload = {
            "campaign_id": 1,
            "ad_group_id": 1,
            "daily_budget": 5000.0,
            "budget_spent_today": 1000.0,
            "bid_strategy": "max_conversions",
            "max_cpc": 5.0,
            "device": "mobile",
            "platform": "simulated",
        }
        while True:
            await self._request(
                client, "POST", "/api/bidding/auction", json=payload, headers=headers
            )

    async def _dashboard_worker(self, client: httpx.AsyncClient) -> None:
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        while True:
            await self._request(client, "GET", "/api/analytics/dashboard", headers=headers)

    async def run(self, duration: int, pattern: str = "mixed") -> Stats:
        """Run load test for specified duration.

        pattern:
            "health"  — health check only
            "api"     — campaign list + dashboard
            "auction" — bidding auction only
            "mixed"   — mix of all endpoints (default)
        """
        limits = httpx.Limits(
            max_keepalive_connections=100,
            max_connections=200,
            keepalive_expiry=30,
        )
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(10.0),
            limits=limits,
        ) as client:
            workers: dict[str, int] = {}

            if pattern == "health":
                workers = {"health": self.concurrency}
            elif pattern == "api":
                workers = {"campaigns": self.concurrency // 2, "dashboard": self.concurrency // 2}
            elif pattern == "auction":
                workers = {"auction": self.concurrency}
            else:  # mixed
                workers = {
                    "health": self.concurrency // 4,
                    "campaigns": self.concurrency // 4,
                    "auction": self.concurrency // 4,
                    "dashboard": self.concurrency // 4,
                }

            worker_map = {
                "health": self._health_check_worker,
                "campaigns": self._campaign_list_worker,
                "auction": self._auction_worker,
                "dashboard": self._dashboard_worker,
            }

            tasks: list[asyncio.Task] = []
            for name, count in workers.items():
                worker_fn = worker_map[name]
                for _ in range(max(count, 1)):
                    tasks.append(asyncio.create_task(worker_fn(client)))

            print(f"Running {pattern} load test with {sum(workers.values())} concurrent workers for {duration}s...")
            t0 = time.time()

            # Print periodic stats
            async def reporter():
                while True:
                    await asyncio.sleep(5)
                    elapsed = time.time() - t0
                    print(f"\n--- {elapsed:.0f}s elapsed, {self.stats.total} requests, "
                          f"{self.stats.success} success, {self.stats.errors} errors ---")

            reporter_task = asyncio.create_task(reporter())

            await asyncio.sleep(duration)
            reporter_task.cancel()

            for task in tasks:
                task.cancel()

        return self.stats


async def main():
    parser = argparse.ArgumentParser(description="Load test for Ad Platform")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL")
    parser.add_argument("--concurrency", type=int, default=1000, help="Concurrent workers")
    parser.add_argument("--duration", type=int, default=30, help="Test duration in seconds")
    parser.add_argument("--pattern", default="mixed",
                        choices=["health", "api", "auction", "mixed"])
    parser.add_argument("--token", default="", help="JWT auth token")
    args = parser.parse_args()

    print(f"=== Ad Platform Load Test ===")
    print(f"URL: {args.url} | Concurrency: {args.concurrency} | Duration: {args.duration}s")

    tester = LoadTester(args.url, args.concurrency, args.token)
    stats = await tester.run(args.duration, args.pattern)

    print(f"\n=== Results ===")
    print(stats.summary())


if __name__ == "__main__":
    asyncio.run(main())
