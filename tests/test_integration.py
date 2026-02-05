"""Integration tests for end-to-end FTL2 execution."""

import tempfile
from pathlib import Path

import pytest

from ftl2.executor import ModuleExecutor
from ftl2.inventory import HostGroup, Inventory
from ftl2.runners import ExecutionContext
from ftl2.types import ExecutionConfig, GateConfig, HostConfig


@pytest.fixture
def localhost_inventory():
    """Create an inventory with just localhost."""
    inventory = Inventory()
    group = HostGroup(name="all")
    group.add_host(
        HostConfig(
            name="localhost",
            ansible_host="127.0.0.1",
            ansible_connection="local",
        )
    )
    inventory.add_group(group)
    return inventory


@pytest.fixture
def test_module_dir():
    """Get path to test modules directory."""
    return Path(__file__).parent / "test_modules"


class TestEndToEndExecution:
    """End-to-end integration tests."""

    async def test_execute_ping_on_localhost(self, localhost_inventory, test_module_dir):
        """Test executing test module on localhost."""
        # Create execution configuration
        exec_config = ExecutionConfig(
            module_name="test_new_style",
            module_dirs=[test_module_dir],
            module_args={},
            modules=["test_new_style"],
        )

        # Create gate configuration
        gate_config = GateConfig()

        # Create execution context
        context = ExecutionContext(
            execution_config=exec_config,
            gate_config=gate_config,
        )

        # Create executor and run
        executor = ModuleExecutor()
        try:
            results = await executor.run(localhost_inventory, context)

            # Verify results
            assert results.total_hosts == 1
            assert results.successful == 1
            assert results.failed == 0
            assert results.is_success()

            # Check localhost result
            assert "localhost" in results.results
            localhost_result = results.results["localhost"]
            assert localhost_result.success
            assert localhost_result.host_name == "localhost"
            assert "msg" in localhost_result.output
            assert "New-style module executed" in localhost_result.output["msg"]

        finally:
            await executor.cleanup()

    async def test_execute_with_module_args(self, localhost_inventory, test_module_dir):
        """Test executing module with arguments."""
        # Create execution configuration with args
        exec_config = ExecutionConfig(
            module_name="test_new_style",
            module_dirs=[test_module_dir],
            module_args={"data": "test message"},
            modules=["test_new_style"],
        )

        gate_config = GateConfig()
        context = ExecutionContext(
            execution_config=exec_config,
            gate_config=gate_config,
        )

        executor = ModuleExecutor()
        try:
            results = await executor.run(localhost_inventory, context)

            assert results.is_success()
            localhost_result = results.results["localhost"]
            assert "received_args" in localhost_result.output
            assert localhost_result.output["received_args"]["data"] == "test message"

        finally:
            await executor.cleanup()

    async def test_execute_multiple_hosts(self, test_module_dir):
        """Test executing on multiple hosts."""
        # Create inventory with multiple local hosts
        inventory = Inventory()
        group = HostGroup(name="all")
        for i in range(1, 4):
            group.add_host(
                HostConfig(
                    name=f"host{i}",
                    ansible_host="127.0.0.1",
                    ansible_connection="local",
                )
            )
        inventory.add_group(group)

        exec_config = ExecutionConfig(
            module_name="test_new_style",
            module_dirs=[test_module_dir],
            module_args={},
            modules=["test_new_style"],
        )

        gate_config = GateConfig()
        context = ExecutionContext(
            execution_config=exec_config,
            gate_config=gate_config,
        )

        executor = ModuleExecutor()
        try:
            results = await executor.run(inventory, context)

            assert results.total_hosts == 3
            assert results.successful == 3
            assert results.failed == 0
            assert results.is_success()

            # All hosts should succeed
            for host_name in ["host1", "host2", "host3"]:
                assert host_name in results.results
                assert results.results[host_name].success

        finally:
            await executor.cleanup()

    async def test_execute_with_host_args(self, test_module_dir):
        """Test executing with host-specific argument overrides."""
        inventory = Inventory()
        group = HostGroup(name="all")
        group.add_host(
            HostConfig(
                name="host1",
                ansible_host="127.0.0.1",
                ansible_connection="local",
            )
        )
        group.add_host(
            HostConfig(
                name="host2",
                ansible_host="127.0.0.1",
                ansible_connection="local",
            )
        )
        inventory.add_group(group)

        # Base args with host-specific override
        exec_config = ExecutionConfig(
            module_name="test_new_style",
            module_dirs=[test_module_dir],
            module_args={"data": "default message"},
            host_args={
                "host1": {"data": "custom message for host1"},
            },
            modules=["test_new_style"],
        )

        gate_config = GateConfig()
        context = ExecutionContext(
            execution_config=exec_config,
            gate_config=gate_config,
        )

        executor = ModuleExecutor()
        try:
            results = await executor.run(inventory, context)

            assert results.is_success()

            # host1 should have custom message
            host1_result = results.results["host1"]
            assert host1_result.output["received_args"]["data"] == "custom message for host1"

            # host2 should have default message
            host2_result = results.results["host2"]
            assert host2_result.output["received_args"]["data"] == "default message"

        finally:
            await executor.cleanup()

    async def test_execute_with_chunking(self, test_module_dir):
        """Test that chunking works correctly with many hosts."""
        # Create 15 hosts (more than default chunk size of 10)
        inventory = Inventory()
        group = HostGroup(name="all")
        for i in range(15):
            group.add_host(
                HostConfig(
                    name=f"host{i}",
                    ansible_host="127.0.0.1",
                    ansible_connection="local",
                )
            )
        inventory.add_group(group)

        exec_config = ExecutionConfig(
            module_name="test_new_style",
            module_dirs=[test_module_dir],
            module_args={},
            modules=["test_new_style"],
        )

        gate_config = GateConfig()
        context = ExecutionContext(
            execution_config=exec_config,
            gate_config=gate_config,
        )

        # Use smaller chunk size to test chunking logic
        executor = ModuleExecutor(chunk_size=5)
        try:
            results = await executor.run(inventory, context)

            assert results.total_hosts == 15
            assert results.successful == 15
            assert results.failed == 0

        finally:
            await executor.cleanup()

    async def test_execute_missing_module(self, localhost_inventory):
        """Test graceful handling of missing module."""
        exec_config = ExecutionConfig(
            module_name="nonexistent_module",
            module_dirs=[Path("/tmp/nonexistent")],
            module_args={},
            modules=["nonexistent_module"],
        )

        gate_config = GateConfig()
        context = ExecutionContext(
            execution_config=exec_config,
            gate_config=gate_config,
        )

        executor = ModuleExecutor()
        try:
            results = await executor.run(localhost_inventory, context)

            # Should have result but marked as failure
            assert results.total_hosts == 1
            assert results.successful == 0
            assert results.failed == 1
            assert not results.is_success()

            localhost_result = results.results["localhost"]
            assert not localhost_result.success
            assert "not found" in localhost_result.error.lower()

        finally:
            await executor.cleanup()

    async def test_execute_from_yaml_inventory(self, test_module_dir):
        """Test executing with inventory loaded from YAML file."""
        # Create temporary YAML inventory
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write("""
all:
  hosts:
    localhost:
      ansible_host: 127.0.0.1
      ansible_connection: local
""")
            inventory_path = f.name

        try:
            # Load inventory from YAML
            from ftl2.inventory import load_inventory

            inventory = load_inventory(inventory_path)

            exec_config = ExecutionConfig(
                module_name="test_new_style",
                module_dirs=[test_module_dir],
                module_args={},
                modules=["test_new_style"],
            )

            gate_config = GateConfig()
            context = ExecutionContext(
                execution_config=exec_config,
                gate_config=gate_config,
            )

            executor = ModuleExecutor()
            try:
                results = await executor.run(inventory, context)

                assert results.is_success()
                assert "localhost" in results.results

            finally:
                await executor.cleanup()

        finally:
            # Clean up temporary file
            Path(inventory_path).unlink(missing_ok=True)
