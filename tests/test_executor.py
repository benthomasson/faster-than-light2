"""Tests for module execution orchestrator."""

from pathlib import Path

import pytest

from ftl2.executor import ExecutionResults, ModuleExecutor
from ftl2.inventory import Inventory, load_localhost
from ftl2.runners import ExecutionContext
from ftl2.types import ExecutionConfig, GateConfig, HostConfig, ModuleResult


class TestExecutionResults:
    """Tests for ExecutionResults dataclass."""

    def test_empty_results(self):
        """Test results with no executions."""
        results = ExecutionResults()
        assert results.results == {}
        assert results.total_hosts == 0
        assert results.successful == 0
        assert results.failed == 0
        assert results.is_success()

    def test_all_successful(self):
        """Test results with all successes."""
        results = ExecutionResults(
            results={
                "host1": ModuleResult(
                    host_name="host1", success=True, changed=False, output={}
                ),
                "host2": ModuleResult(
                    host_name="host2", success=True, changed=False, output={}
                ),
            }
        )
        assert results.total_hosts == 2
        assert results.successful == 2
        assert results.failed == 0
        assert results.is_success()

    def test_some_failures(self):
        """Test results with some failures."""
        results = ExecutionResults(
            results={
                "host1": ModuleResult(
                    host_name="host1", success=True, changed=False, output={}
                ),
                "host2": ModuleResult(
                    host_name="host2", success=False, changed=False, output={}, error="Failed"
                ),
            }
        )
        assert results.total_hosts == 2
        assert results.successful == 1
        assert results.failed == 1
        assert not results.is_success()

    def test_all_failures(self):
        """Test results with all failures."""
        results = ExecutionResults(
            results={
                "host1": ModuleResult(
                    host_name="host1",
                    success=False,
                    changed=False,
                    output={},
                    error="Error 1",
                ),
                "host2": ModuleResult(
                    host_name="host2",
                    success=False,
                    changed=False,
                    output={},
                    error="Error 2",
                ),
            }
        )
        assert results.total_hosts == 2
        assert results.successful == 0
        assert results.failed == 2
        assert not results.is_success()


class TestModuleExecutor:
    """Tests for ModuleExecutor."""

    def test_create_executor(self):
        """Test creating an executor."""
        executor = ModuleExecutor()
        assert executor.runner_factory is not None
        assert executor.chunk_size == 10

    def test_custom_chunk_size(self):
        """Test creating executor with custom chunk size."""
        executor = ModuleExecutor(chunk_size=5)
        assert executor.chunk_size == 5

    @pytest.mark.asyncio
    async def test_cleanup(self):
        """Test cleanup method."""
        executor = ModuleExecutor()
        # Should not raise
        await executor.cleanup()


class TestModuleExecutorIntegration:
    """Integration tests for ModuleExecutor."""

    @pytest.fixture
    def test_modules_dir(self) -> Path:
        """Get path to test modules directory."""
        return Path(__file__).parent / "test_modules"

    @pytest.fixture
    def localhost_inventory(self) -> Inventory:
        """Create localhost inventory."""
        return load_localhost()

    @pytest.fixture
    def context(self, test_modules_dir: Path) -> ExecutionContext:
        """Create execution context for testing."""
        return ExecutionContext(
            execution_config=ExecutionConfig(
                module_name="test_binary.sh", module_dirs=[test_modules_dir]
            ),
            gate_config=GateConfig(),
        )

    @pytest.mark.asyncio
    async def test_run_on_localhost(
        self, localhost_inventory: Inventory, context: ExecutionContext
    ):
        """Test running module on localhost."""
        executor = ModuleExecutor()

        results = await executor.run(localhost_inventory, context)

        assert results.total_hosts == 1
        assert results.successful == 1
        assert results.failed == 0
        assert results.is_success()

        # Check result for localhost
        assert "localhost" in results.results
        localhost_result = results.results["localhost"]
        assert localhost_result.success
        assert localhost_result.host_name == "localhost"

    @pytest.mark.asyncio
    async def test_run_multiple_hosts(self, test_modules_dir: Path):
        """Test running module on multiple hosts."""
        # Create inventory with multiple localhost entries
        from ftl2.inventory import HostGroup

        inventory = Inventory()
        group = HostGroup(name="local_hosts")
        group.add_host(
            HostConfig(
                name="local1", ansible_host="127.0.0.1", ansible_connection="local"
            )
        )
        group.add_host(
            HostConfig(
                name="local2", ansible_host="127.0.0.1", ansible_connection="local"
            )
        )
        group.add_host(
            HostConfig(
                name="local3", ansible_host="127.0.0.1", ansible_connection="local"
            )
        )
        inventory.add_group(group)

        context = ExecutionContext(
            execution_config=ExecutionConfig(
                module_name="test_binary.sh", module_dirs=[test_modules_dir]
            ),
            gate_config=GateConfig(),
        )

        executor = ModuleExecutor()
        results = await executor.run(inventory, context)

        assert results.total_hosts == 3
        assert results.successful == 3
        assert results.failed == 0
        assert results.is_success()

        # All hosts should have results
        assert "local1" in results.results
        assert "local2" in results.results
        assert "local3" in results.results

    @pytest.mark.asyncio
    async def test_run_with_module_not_found(self, localhost_inventory: Inventory):
        """Test execution when module doesn't exist."""
        context = ExecutionContext(
            execution_config=ExecutionConfig(
                module_name="nonexistent_module", module_dirs=[Path("/tmp")]
            ),
            gate_config=GateConfig(),
        )

        executor = ModuleExecutor()
        results = await executor.run(localhost_inventory, context)

        # Should have one failed result
        assert results.total_hosts == 1
        assert results.successful == 0
        assert results.failed == 1
        assert not results.is_success()

        # Check error
        result = results.results["localhost"]
        assert not result.success
        assert result.error is not None
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_chunking(self, test_modules_dir: Path):
        """Test that chunking works correctly."""
        # Create inventory with more hosts than chunk size
        from ftl2.inventory import HostGroup

        inventory = Inventory()
        group = HostGroup(name="test_hosts")
        for i in range(15):
            group.add_host(
                HostConfig(
                    name=f"host{i}", ansible_host="127.0.0.1", ansible_connection="local"
                )
            )
        inventory.add_group(group)

        context = ExecutionContext(
            execution_config=ExecutionConfig(
                module_name="test_binary.sh", module_dirs=[test_modules_dir]
            ),
            gate_config=GateConfig(),
        )

        # Use small chunk size
        executor = ModuleExecutor(chunk_size=5)
        results = await executor.run(inventory, context)

        # All hosts should complete successfully
        assert results.total_hosts == 15
        assert results.successful == 15
        assert results.failed == 0

    @pytest.mark.asyncio
    async def test_cleanup_after_execution(
        self, localhost_inventory: Inventory, context: ExecutionContext
    ):
        """Test cleanup after execution."""
        executor = ModuleExecutor()

        # Run execution
        await executor.run(localhost_inventory, context)

        # Cleanup should work
        await executor.cleanup()

        # Can run again after cleanup
        results = await executor.run(localhost_inventory, context)
        assert results.successful == 1
