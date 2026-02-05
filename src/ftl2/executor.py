"""Module execution orchestration for FTL2.

This module provides the core orchestration logic for running modules
across inventories of hosts with concurrent execution, chunking for
optimal performance, and result aggregation.
"""

import asyncio
import logging
from dataclasses import dataclass, field

from .inventory import Inventory
from .runners import ExecutionContext, ModuleRunnerFactory
from .types import HostConfig, ModuleResult
from .utils import chunk

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResults:
    """Results from executing a module across multiple hosts.

    Attributes:
        results: Dictionary mapping host names to their execution results
        total_hosts: Total number of hosts executed against
        successful: Number of successful executions
        failed: Number of failed executions

    Example:
        >>> results = ExecutionResults(
        ...     results={"host1": ModuleResult(...), "host2": ModuleResult(...)},
        ...     total_hosts=2,
        ...     successful=2,
        ...     failed=0
        ... )
    """

    results: dict[str, ModuleResult] = field(default_factory=dict)
    total_hosts: int = 0
    successful: int = 0
    failed: int = 0

    def __post_init__(self) -> None:
        """Calculate statistics from results."""
        if not self.results:
            return

        self.total_hosts = len(self.results)
        self.successful = sum(1 for r in self.results.values() if r.success)
        self.failed = self.total_hosts - self.successful

    def is_success(self) -> bool:
        """Check if all executions succeeded."""
        return self.failed == 0


class ModuleExecutor:
    """Orchestrates module execution across inventories of hosts.

    Manages concurrent execution with chunking, result aggregation,
    and proper cleanup of resources.

    Attributes:
        runner_factory: Factory for creating module runners
        chunk_size: Number of hosts to process concurrently

    Example:
        >>> executor = ModuleExecutor()
        >>> context = ExecutionContext(
        ...     execution_config=ExecutionConfig(module_name="ping"),
        ...     gate_config=GateConfig()
        ... )
        >>> results = await executor.run(inventory, context)
        >>> print(f"Success: {results.successful}/{results.total_hosts}")
    """

    def __init__(self, chunk_size: int = 10) -> None:
        """Initialize the executor.

        Args:
            chunk_size: Number of hosts to process concurrently (default: 10)
        """
        self.runner_factory = ModuleRunnerFactory()
        self.chunk_size = chunk_size

    async def run(
        self,
        inventory: Inventory,
        context: ExecutionContext,
    ) -> ExecutionResults:
        """Execute a module across all hosts in the inventory.

        Args:
            inventory: Inventory of hosts to execute against
            context: Execution context with module and gate config

        Returns:
            ExecutionResults with per-host results and statistics

        Example:
            >>> inventory = load_inventory(Path("hosts.yaml"))
            >>> results = await executor.run(inventory, context)
            >>> for host, result in results.results.items():
            ...     print(f"{host}: {result.success}")
        """
        hosts = inventory.get_all_hosts()
        all_results: dict[str, ModuleResult] = {}

        # Process hosts in chunks for optimal performance
        for host_chunk in chunk(list(hosts.values()), self.chunk_size):
            chunk_results = await self._execute_chunk(host_chunk, context)
            all_results.update(chunk_results)

        return ExecutionResults(results=all_results)

    async def _execute_chunk(
        self,
        hosts: list[HostConfig],
        context: ExecutionContext,
    ) -> dict[str, ModuleResult]:
        """Execute module on a chunk of hosts concurrently.

        Args:
            hosts: List of hosts to execute against
            context: Execution context

        Returns:
            Dictionary mapping host names to results
        """
        tasks: list[tuple[str, asyncio.Task[ModuleResult]]] = []

        for host in hosts:
            # Get appropriate runner (local or remote)
            runner = self.runner_factory.create_runner(host)

            # Create task for this host
            task = asyncio.create_task(runner.run(host, context))
            tasks.append((host.name, task))

        # Wait for all tasks to complete
        await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)

        # Extract results
        results: dict[str, ModuleResult] = {}
        for host_name, task in tasks:
            try:
                result = task.result()
                results[host_name] = result
            except Exception as e:
                # Convert exception to error result
                logger.exception(f"Execution failed on {host_name}: {e}")
                results[host_name] = ModuleResult(
                    host_name=host_name,
                    success=False,
                    changed=False,
                    output={},
                    error=str(e),
                )

        return results

    async def cleanup(self) -> None:
        """Clean up all runner resources."""
        await self.runner_factory.cleanup_all()
