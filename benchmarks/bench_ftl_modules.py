#!/usr/bin/env python3
"""Benchmarks for FTL Modules vs Ansible modules.

Measures the performance difference between:
1. FTL modules (in-process Python functions)
2. Ansible modules (subprocess execution)

Target: 250x speedup for local execution.
"""

import asyncio
import json
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def time_it(func, iterations=100):
    """Time a function over multiple iterations."""
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        func()
        end = time.perf_counter()
        times.append(end - start)
    return times


async def time_it_async(func, iterations=100):
    """Time an async function over multiple iterations."""
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        await func()
        end = time.perf_counter()
        times.append(end - start)
    return times


def run_ansible_module(module_name: str, args: dict) -> dict:
    """Run an Ansible module via subprocess (simulating Ansible's approach)."""
    # This simulates how Ansible runs modules - via subprocess
    module_args = json.dumps({"ANSIBLE_MODULE_ARGS": args})

    # Use python to run a simple module simulation
    code = f'''
import json
import sys
args = json.loads(sys.stdin.read())["ANSIBLE_MODULE_ARGS"]
result = {{"changed": False, "msg": "ok"}}
print(json.dumps(result))
'''

    result = subprocess.run(
        [sys.executable, "-c", code],
        input=module_args,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def benchmark_file_module():
    """Benchmark file module: FTL vs subprocess overhead."""
    print("\n" + "=" * 60)
    print("BENCHMARK: File Module (touch)")
    print("=" * 60)

    from ftl2.ftl_modules import ftl_file

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.txt"

        # Warm up
        ftl_file(path=str(test_file), state="touch")
        test_file.unlink()

        # Benchmark FTL module
        def run_ftl():
            ftl_file(path=str(test_file), state="touch")
            test_file.unlink()

        ftl_times = time_it(run_ftl, iterations=100)

        # Benchmark subprocess (simulating Ansible)
        def run_subprocess():
            run_ansible_module("file", {"path": str(test_file), "state": "touch"})

        subprocess_times = time_it(run_subprocess, iterations=100)

        print_results("FTL file module", ftl_times)
        print_results("Subprocess (Ansible-style)", subprocess_times)
        print_speedup(ftl_times, subprocess_times)


def benchmark_command_module():
    """Benchmark command module."""
    print("\n" + "=" * 60)
    print("BENCHMARK: Command Module")
    print("=" * 60)

    from ftl2.ftl_modules import ftl_command

    # Benchmark FTL module
    def run_ftl():
        ftl_command(cmd="echo hello")

    ftl_times = time_it(run_ftl, iterations=100)

    # Benchmark subprocess wrapper
    def run_subprocess():
        run_ansible_module("command", {"cmd": "echo hello"})

    subprocess_times = time_it(run_subprocess, iterations=100)

    print_results("FTL command module", ftl_times)
    print_results("Subprocess (Ansible-style)", subprocess_times)
    print_speedup(ftl_times, subprocess_times)


async def benchmark_async_http():
    """Benchmark async HTTP module."""
    print("\n" + "=" * 60)
    print("BENCHMARK: HTTP Module (mocked)")
    print("=" * 60)

    from unittest.mock import AsyncMock, MagicMock, patch
    from ftl2.ftl_modules import ftl_uri

    # Mock HTTP client to measure just the module overhead
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.url = "https://example.com/"
    mock_response.text = "response"
    mock_response.headers = {"content-type": "text/html"}

    mock_client = AsyncMock()
    mock_client.request.return_value = mock_response

    # Benchmark FTL async module
    async def run_ftl():
        with patch("ftl2.ftl_modules.http.httpx.AsyncClient") as mock:
            mock.return_value.__aenter__.return_value = mock_client
            await ftl_uri(url="https://example.com/")

    ftl_times = await time_it_async(run_ftl, iterations=100)

    # Benchmark subprocess
    def run_subprocess():
        run_ansible_module("uri", {"url": "https://example.com/"})

    subprocess_times = time_it(run_subprocess, iterations=100)

    print_results("FTL uri module (async)", ftl_times)
    print_results("Subprocess (Ansible-style)", subprocess_times)
    print_speedup(ftl_times, subprocess_times)


async def benchmark_executor():
    """Benchmark the executor path selection."""
    print("\n" + "=" * 60)
    print("BENCHMARK: Executor (execute function)")
    print("=" * 60)

    from ftl2.ftl_modules import execute

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.txt"

        async def run_execute():
            await execute("file", {"path": str(test_file), "state": "touch"})
            if test_file.exists():
                test_file.unlink()

        times = await time_it_async(run_execute, iterations=100)

        print_results("execute() with FTL module", times)


async def benchmark_concurrent_execution():
    """Benchmark concurrent execution on multiple 'hosts'."""
    print("\n" + "=" * 60)
    print("BENCHMARK: Concurrent Execution (execute_on_hosts)")
    print("=" * 60)

    from ftl2.ftl_modules import execute_on_hosts, LocalHost

    for num_hosts in [10, 50, 100]:
        hosts = [LocalHost(name=f"host{i}") for i in range(num_hosts)]

        async def run_concurrent():
            await execute_on_hosts(hosts, "command", {"cmd": "echo hello"})

        times = await time_it_async(run_concurrent, iterations=10)

        print(f"\n{num_hosts} hosts:")
        print_results(f"  execute_on_hosts ({num_hosts} concurrent)", times)

        # Calculate per-host time
        avg_total = statistics.mean(times)
        per_host = avg_total / num_hosts
        print(f"  Per-host average: {per_host*1000:.3f}ms")


async def benchmark_batch_execution():
    """Benchmark batch execution of different modules."""
    print("\n" + "=" * 60)
    print("BENCHMARK: Batch Execution (execute_batch)")
    print("=" * 60)

    from ftl2.ftl_modules import execute_batch

    with tempfile.TemporaryDirectory() as tmpdir:
        for batch_size in [5, 10, 20]:
            tasks = []
            for i in range(batch_size):
                if i % 2 == 0:
                    tasks.append(("command", {"cmd": "echo hello"}, None))
                else:
                    tasks.append(("file", {"path": f"{tmpdir}/file{i}.txt", "state": "touch"}, None))

            async def run_batch():
                await execute_batch(tasks)

            times = await time_it_async(run_batch, iterations=10)

            print(f"\n{batch_size} tasks:")
            print_results(f"  execute_batch ({batch_size} tasks)", times)


def benchmark_module_lookup():
    """Benchmark module registry lookup."""
    print("\n" + "=" * 60)
    print("BENCHMARK: Module Registry Lookup")
    print("=" * 60)

    from ftl2.ftl_modules import get_module, has_ftl_module

    # Benchmark get_module by short name
    def lookup_short():
        get_module("file")
        get_module("copy")
        get_module("command")
        get_module("uri")

    times = time_it(lookup_short, iterations=10000)
    print_results("get_module (short name, 4 lookups)", times)

    # Benchmark get_module by FQCN
    def lookup_fqcn():
        get_module("ansible.builtin.file")
        get_module("ansible.builtin.copy")
        get_module("ansible.builtin.command")
        get_module("ansible.builtin.uri")

    times = time_it(lookup_fqcn, iterations=10000)
    print_results("get_module (FQCN, 4 lookups)", times)

    # Benchmark has_ftl_module
    def check_has():
        has_ftl_module("file")
        has_ftl_module("nonexistent")

    times = time_it(check_has, iterations=10000)
    print_results("has_ftl_module (2 checks)", times)


def print_results(name: str, times: list[float]):
    """Print benchmark results."""
    avg = statistics.mean(times)
    std = statistics.stdev(times) if len(times) > 1 else 0
    min_t = min(times)
    max_t = max(times)

    print(f"\n{name}:")
    print(f"  Average: {avg*1000:.3f}ms")
    print(f"  Std Dev: {std*1000:.3f}ms")
    print(f"  Min:     {min_t*1000:.3f}ms")
    print(f"  Max:     {max_t*1000:.3f}ms")


def print_speedup(ftl_times: list[float], subprocess_times: list[float]):
    """Print speedup comparison."""
    ftl_avg = statistics.mean(ftl_times)
    subprocess_avg = statistics.mean(subprocess_times)
    speedup = subprocess_avg / ftl_avg if ftl_avg > 0 else float('inf')

    print(f"\n>>> SPEEDUP: {speedup:.1f}x faster with FTL")


async def main():
    """Run all benchmarks."""
    print("=" * 60)
    print("FTL MODULES BENCHMARK SUITE")
    print("=" * 60)
    print(f"Python: {sys.version}")
    print(f"Platform: {sys.platform}")

    # Sync benchmarks
    benchmark_module_lookup()
    benchmark_file_module()
    benchmark_command_module()

    # Async benchmarks
    await benchmark_async_http()
    await benchmark_executor()
    await benchmark_concurrent_execution()
    await benchmark_batch_execution()

    print("\n" + "=" * 60)
    print("BENCHMARK COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
