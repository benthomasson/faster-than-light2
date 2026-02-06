# FTL Modules Benchmark Results

**Date:** 2026-02-06
**Python:** 3.13.3
**Platform:** macOS (darwin)

## Summary

FTL modules achieve significant performance improvements over traditional subprocess-based Ansible module execution:

| Module | FTL Time | Subprocess Time | Speedup |
|--------|----------|-----------------|---------|
| file (touch) | 0.069ms | 22.6ms | **330x** |
| uri (mocked) | 0.277ms | 23.4ms | **84x** |
| command | 3.2ms | 22.9ms | **7.2x** |

The file module exceeds the 250x target speedup. The command module shows lower speedup because both approaches must spawn a subprocess for the actual command.

## Module Registry Performance

Registry lookups are sub-microsecond:

| Operation | Average Time |
|-----------|--------------|
| get_module (short name) | <0.001ms |
| get_module (FQCN) | <0.001ms |
| has_ftl_module | <0.001ms |

## Executor Performance

The async executor with FTL module path selection:

| Operation | Average Time |
|-----------|--------------|
| execute() single call | 0.160ms |

## Concurrent Execution Scaling

Using `execute_on_hosts()` with multiple LocalHost instances:

| Hosts | Total Time | Per-Host Time |
|-------|------------|---------------|
| 10 | 13.9ms | 1.39ms |
| 50 | 65.1ms | 1.30ms |
| 100 | 129.0ms | 1.29ms |

Per-host time remains constant as scale increases, demonstrating linear scaling.

## Batch Execution

Using `execute_batch()` with mixed module types:

| Tasks | Total Time | Per-Task Time |
|-------|------------|---------------|
| 5 | 6.4ms | 1.27ms |
| 10 | 8.8ms | 0.88ms |
| 20 | 15.8ms | 0.79ms |

## Async vs Fork Memory Comparison

Comparing async execution (FTL approach) vs fork-based execution (Ansible approach):

### Speed Comparison

| Tasks | Fork Time | Async Time | Speedup |
|-------|-----------|------------|---------|
| 10 | 134ms | 11ms | **12x** |
| 50 | 148ms | 11ms | **13x** |
| 100 | 219ms | 12ms | **19x** |
| 200 | 332ms | 12ms | **27x** |

Async speedup increases with scale because fork overhead grows while async overhead stays constant.

### Memory Comparison

| Tasks | Fork Memory Delta | Async Memory Delta | Ratio |
|-------|-------------------|-------------------|-------|
| 10 | 2.0 MB | ~0 MB | **20x** |
| 50 | 0.3 MB | ~0 MB | **3x** |
| 100 | 0.2 MB | ~0 MB | **2.5x** |
| 200 | 0.1 MB | 0.1 MB | **1.3x** |

Fork memory overhead is higher at lower scales due to pool initialization.

## FTL Executor Scaling

Real-world scaling with the FTL executor:

| Hosts | Duration | Memory Delta | Per-Host Time |
|-------|----------|--------------|---------------|
| 10 | 17ms | 0.6 MB | 1.70ms |
| 50 | 61ms | 1.5 MB | 1.23ms |
| 100 | 122ms | 0.8 MB | 1.22ms |
| 200 | 246ms | 0.7 MB | 1.23ms |

- 100% success rate at all scales
- Linear time scaling (O(n))
- Constant per-host time (~1.2ms)
- Minimal memory growth

## Conclusions

1. **FTL modules are 84-330x faster** than subprocess-based execution for in-process operations
2. **Async execution scales better** than fork-based execution (up to 27x faster at 200 tasks)
3. **Memory usage is minimal** with async (near-zero overhead vs 2MB+ for fork pools)
4. **Linear scaling** demonstrated up to 200 concurrent hosts
5. **Consistent per-host time** (~1.2ms) regardless of scale

## Running Benchmarks

```bash
# Module performance benchmarks
uv run python benchmarks/bench_ftl_modules.py

# Memory and scaling benchmarks
uv run python benchmarks/bench_memory.py
```
