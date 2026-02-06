#!/usr/bin/env python3
"""Memory benchmarks for async vs fork at scale.

Measures memory usage when running concurrent operations:
1. Async execution (FTL approach)
2. Fork-based execution (Ansible approach simulation)

This demonstrates the memory efficiency of async/await vs forking.
"""

import asyncio
import multiprocessing
import os
import resource
import sys
import time
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def get_memory_mb() -> float:
    """Get current process memory usage in MB."""
    rusage = resource.getrusage(resource.RUSAGE_SELF)
    # maxrss is in bytes on Linux, KB on macOS
    if sys.platform == "darwin":
        return rusage.ru_maxrss / 1024 / 1024  # KB to MB
    else:
        return rusage.ru_maxrss / 1024  # bytes to MB


def fork_worker(task_id: int) -> dict:
    """Simulate work in a forked process."""
    # Simulate some work
    time.sleep(0.01)
    return {"task_id": task_id, "pid": os.getpid()}


async def async_worker(task_id: int) -> dict:
    """Simulate work in async coroutine."""
    await asyncio.sleep(0.01)
    return {"task_id": task_id}


def benchmark_fork(num_tasks: int, max_workers: int = 10) -> dict:
    """Benchmark fork-based execution (Ansible-style)."""
    start_mem = get_memory_mb()
    start_time = time.perf_counter()

    # Use multiprocessing pool to simulate Ansible's fork approach
    with multiprocessing.Pool(processes=max_workers) as pool:
        results = pool.map(fork_worker, range(num_tasks))

    end_time = time.perf_counter()
    end_mem = get_memory_mb()

    return {
        "method": "fork",
        "num_tasks": num_tasks,
        "max_workers": max_workers,
        "duration_s": end_time - start_time,
        "start_mem_mb": start_mem,
        "peak_mem_mb": end_mem,
        "mem_delta_mb": end_mem - start_mem,
    }


async def benchmark_async(num_tasks: int) -> dict:
    """Benchmark async execution (FTL-style)."""
    start_mem = get_memory_mb()
    start_time = time.perf_counter()

    # Run all tasks concurrently with asyncio.gather
    tasks = [async_worker(i) for i in range(num_tasks)]
    results = await asyncio.gather(*tasks)

    end_time = time.perf_counter()
    end_mem = get_memory_mb()

    return {
        "method": "async",
        "num_tasks": num_tasks,
        "duration_s": end_time - start_time,
        "start_mem_mb": start_mem,
        "peak_mem_mb": end_mem,
        "mem_delta_mb": end_mem - start_mem,
    }


async def benchmark_ftl_executor(num_hosts: int) -> dict:
    """Benchmark FTL executor with multiple hosts."""
    from ftl2.ftl_modules import execute_on_hosts, LocalHost

    hosts = [LocalHost(name=f"host{i}") for i in range(num_hosts)]

    start_mem = get_memory_mb()
    start_time = time.perf_counter()

    results = await execute_on_hosts(hosts, "command", {"cmd": "echo hello"})

    end_time = time.perf_counter()
    end_mem = get_memory_mb()

    success_count = sum(1 for r in results if r.success)

    return {
        "method": "ftl_executor",
        "num_hosts": num_hosts,
        "success_count": success_count,
        "duration_s": end_time - start_time,
        "start_mem_mb": start_mem,
        "peak_mem_mb": end_mem,
        "mem_delta_mb": end_mem - start_mem,
    }


def print_result(result: dict):
    """Print benchmark result."""
    method = result["method"]
    if "num_hosts" in result:
        count = result["num_hosts"]
        label = "hosts"
    else:
        count = result["num_tasks"]
        label = "tasks"

    print(f"\n{method.upper()} ({count} {label}):")
    print(f"  Duration:    {result['duration_s']:.3f}s")
    print(f"  Start mem:   {result['start_mem_mb']:.1f} MB")
    print(f"  Peak mem:    {result['peak_mem_mb']:.1f} MB")
    print(f"  Memory delta: {result['mem_delta_mb']:.1f} MB")

    if "success_count" in result:
        print(f"  Successes:   {result['success_count']}/{count}")


async def main():
    """Run memory benchmarks."""
    print("=" * 60)
    print("MEMORY BENCHMARK: Async vs Fork")
    print("=" * 60)
    print(f"Python: {sys.version}")
    print(f"Platform: {sys.platform}")
    print(f"Initial memory: {get_memory_mb():.1f} MB")

    # Test at different scales
    scales = [10, 50, 100, 200]

    print("\n" + "-" * 60)
    print("ASYNC vs FORK COMPARISON")
    print("-" * 60)

    for num_tasks in scales:
        print(f"\n{'='*40}")
        print(f"SCALE: {num_tasks} tasks")
        print(f"{'='*40}")

        # Fork benchmark
        fork_result = benchmark_fork(num_tasks, max_workers=min(num_tasks, 10))
        print_result(fork_result)

        # Async benchmark
        async_result = await benchmark_async(num_tasks)
        print_result(async_result)

        # Comparison
        speedup = fork_result["duration_s"] / async_result["duration_s"]
        mem_ratio = fork_result["mem_delta_mb"] / max(async_result["mem_delta_mb"], 0.1)
        print(f"\n  Async is {speedup:.1f}x faster")
        print(f"  Fork uses {mem_ratio:.1f}x more memory")

    print("\n" + "-" * 60)
    print("FTL EXECUTOR SCALING")
    print("-" * 60)

    for num_hosts in scales:
        result = await benchmark_ftl_executor(num_hosts)
        print_result(result)

        # Per-host metrics
        per_host_time = result["duration_s"] / num_hosts * 1000
        print(f"  Per-host time: {per_host_time:.2f}ms")

    print("\n" + "=" * 60)
    print("MEMORY BENCHMARK COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
