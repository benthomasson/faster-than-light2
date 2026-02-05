"""Tests for module runner interfaces and implementations."""

from pathlib import Path

import pytest

from ftl2.runners import (
    ExecutionContext,
    LocalModuleRunner,
    ModuleRunner,
    ModuleRunnerFactory,
    RemoteModuleRunner,
)
from ftl2.types import ExecutionConfig, GateConfig, HostConfig


class TestExecutionContext:
    """Tests for ExecutionContext dataclass."""

    def test_minimal_context(self):
        """Test creating context with minimal configuration."""
        exec_config = ExecutionConfig(module_name="ping")
        gate_config = GateConfig()

        context = ExecutionContext(execution_config=exec_config, gate_config=gate_config)

        assert context.execution_config == exec_config
        assert context.gate_config == gate_config
        assert context.module_dirs_override == []

    def test_context_with_override(self):
        """Test creating context with module_dirs override."""
        exec_config = ExecutionConfig(module_name="setup")
        gate_config = GateConfig()

        context = ExecutionContext(
            execution_config=exec_config,
            gate_config=gate_config,
            module_dirs_override=["/opt/modules"],
        )

        assert context.module_dirs_override == ["/opt/modules"]

    def test_module_name_property(self):
        """Test module_name property."""
        exec_config = ExecutionConfig(module_name="ping")
        gate_config = GateConfig()
        context = ExecutionContext(execution_config=exec_config, gate_config=gate_config)

        assert context.module_name == "ping"

    def test_module_args_property(self):
        """Test module_args property."""
        exec_config = ExecutionConfig(module_name="command", module_args={"cmd": "echo hello"})
        gate_config = GateConfig()
        context = ExecutionContext(execution_config=exec_config, gate_config=gate_config)

        assert context.module_args == {"cmd": "echo hello"}


class TestModuleRunner:
    """Tests for ModuleRunner ABC."""

    def test_cannot_instantiate_abc(self):
        """Test that ModuleRunner cannot be instantiated directly."""
        with pytest.raises(TypeError):
            ModuleRunner()  # type: ignore


class TestLocalModuleRunner:
    """Tests for LocalModuleRunner."""

    @pytest.mark.asyncio
    async def test_create_local_runner(self):
        """Test creating a local runner instance."""
        runner = LocalModuleRunner()
        assert isinstance(runner, ModuleRunner)
        assert isinstance(runner, LocalModuleRunner)

    @pytest.mark.asyncio
    async def test_cleanup_no_op(self):
        """Test that cleanup is a no-op for local runner."""
        runner = LocalModuleRunner()
        # Should not raise
        await runner.cleanup()

    @pytest.mark.asyncio
    async def test_run_module_not_found(self):
        """Test run() when module is not found."""
        runner = LocalModuleRunner()
        host = HostConfig(
            name="localhost",
            ansible_host="127.0.0.1",
            ansible_connection="local",
        )
        context = ExecutionContext(
            execution_config=ExecutionConfig(module_name="nonexistent"),
            gate_config=GateConfig(),
        )

        result = await runner.run(host, context)

        assert result.is_failure
        assert "not found" in result.error.lower()


class TestRemoteModuleRunner:
    """Tests for RemoteModuleRunner."""

    @pytest.mark.asyncio
    async def test_create_remote_runner(self):
        """Test creating a remote runner instance."""
        runner = RemoteModuleRunner()
        assert isinstance(runner, ModuleRunner)
        assert isinstance(runner, RemoteModuleRunner)
        assert runner.gate_cache == {}

    @pytest.mark.asyncio
    async def test_cleanup_clears_cache(self):
        """Test that cleanup clears the gate cache."""
        runner = RemoteModuleRunner()
        # Simulate some cached gates
        runner.gate_cache["host1"] = "gate1"
        runner.gate_cache["host2"] = "gate2"

        await runner.cleanup()

        assert runner.gate_cache == {}

    @pytest.mark.asyncio
    async def test_run_not_implemented(self):
        """Test that run() raises NotImplementedError."""
        runner = RemoteModuleRunner()
        host = HostConfig(name="web01", ansible_host="192.168.1.10")
        context = ExecutionContext(
            execution_config=ExecutionConfig(module_name="ping"),
            gate_config=GateConfig(),
        )

        with pytest.raises(NotImplementedError):
            await runner.run(host, context)


class TestModuleRunnerFactory:
    """Tests for ModuleRunnerFactory."""

    def test_create_factory(self):
        """Test creating a factory instance."""
        factory = ModuleRunnerFactory()
        assert factory._local_runner is None
        assert factory._remote_runner is None

    def test_create_local_runner(self):
        """Test factory creates LocalModuleRunner for local hosts."""
        factory = ModuleRunnerFactory()
        local_host = HostConfig(
            name="localhost",
            ansible_host="127.0.0.1",
            ansible_connection="local",
        )

        runner = factory.create_runner(local_host)

        assert isinstance(runner, LocalModuleRunner)
        assert factory._local_runner is not None

    def test_create_remote_runner(self):
        """Test factory creates RemoteModuleRunner for remote hosts."""
        factory = ModuleRunnerFactory()
        remote_host = HostConfig(name="web01", ansible_host="192.168.1.10")

        runner = factory.create_runner(remote_host)

        assert isinstance(runner, RemoteModuleRunner)
        assert factory._remote_runner is not None

    def test_runner_reuse(self):
        """Test that factory reuses runner instances."""
        factory = ModuleRunnerFactory()

        host1 = HostConfig(name="localhost", ansible_host="127.0.0.1", ansible_connection="local")
        host2 = HostConfig(name="localhost2", ansible_host="127.0.0.1", ansible_connection="local")

        runner1 = factory.create_runner(host1)
        runner2 = factory.create_runner(host2)

        # Should be the same instance
        assert runner1 is runner2

    def test_different_runner_types(self):
        """Test factory creates different runner types correctly."""
        factory = ModuleRunnerFactory()

        local_host = HostConfig(
            name="localhost", ansible_host="127.0.0.1", ansible_connection="local"
        )
        remote_host = HostConfig(name="web01", ansible_host="192.168.1.10")

        local_runner = factory.create_runner(local_host)
        remote_runner = factory.create_runner(remote_host)

        assert isinstance(local_runner, LocalModuleRunner)
        assert isinstance(remote_runner, RemoteModuleRunner)
        assert local_runner is not remote_runner

    @pytest.mark.asyncio
    async def test_cleanup_all(self):
        """Test cleanup_all cleans up all created runners."""
        factory = ModuleRunnerFactory()

        local_host = HostConfig(
            name="localhost", ansible_host="127.0.0.1", ansible_connection="local"
        )
        remote_host = HostConfig(name="web01", ansible_host="192.168.1.10")

        # Create both runner types
        factory.create_runner(local_host)
        remote_runner = factory.create_runner(remote_host)

        # Add something to remote cache
        remote_runner.gate_cache["test"] = "gate"

        # Cleanup all
        await factory.cleanup_all()

        # Remote cache should be cleared
        assert remote_runner.gate_cache == {}

    @pytest.mark.asyncio
    async def test_cleanup_all_no_runners(self):
        """Test cleanup_all when no runners have been created."""
        factory = ModuleRunnerFactory()
        # Should not raise
        await factory.cleanup_all()


class TestLocalModuleRunnerIntegration:
    """Integration tests for LocalModuleRunner with actual modules."""

    @pytest.fixture
    def test_modules_dir(self) -> Path:
        """Get path to test modules directory."""
        return Path(__file__).parent / "test_modules"

    @pytest.fixture
    def localhost(self) -> HostConfig:
        """Create a localhost configuration."""
        return HostConfig(
            name="localhost",
            ansible_host="127.0.0.1",
            ansible_connection="local",
        )

    @pytest.mark.asyncio
    async def test_run_binary_module(self, localhost: HostConfig, test_modules_dir: Path):
        """Test executing a binary module."""
        runner = LocalModuleRunner()
        context = ExecutionContext(
            execution_config=ExecutionConfig(
                module_name="test_binary.sh",
                module_dirs=[test_modules_dir],
                module_args={"foo": "bar", "test": "value"},
            ),
            gate_config=GateConfig(),
        )

        result = await runner.run(localhost, context)

        assert result.is_success
        assert result.host_name == "localhost"
        assert "msg" in result.output
        assert result.output["msg"] == "Binary module executed"
        assert not result.changed

    @pytest.mark.asyncio
    async def test_run_want_json_module(self, localhost: HostConfig, test_modules_dir: Path):
        """Test executing a WANT_JSON module."""
        runner = LocalModuleRunner()
        context = ExecutionContext(
            execution_config=ExecutionConfig(
                module_name="test_want_json",
                module_dirs=[test_modules_dir],
                module_args={"param1": "value1", "param2": "value2"},
            ),
            gate_config=GateConfig(),
        )

        result = await runner.run(localhost, context)

        assert result.is_success
        assert result.host_name == "localhost"
        assert result.output["msg"] == "WANT_JSON module executed"
        assert "received_args" in result.output
        assert result.output["received_args"]["param1"] == "value1"
        assert not result.changed

    @pytest.mark.asyncio
    async def test_run_want_json_module_with_change(
        self, localhost: HostConfig, test_modules_dir: Path
    ):
        """Test WANT_JSON module that reports changes."""
        runner = LocalModuleRunner()
        context = ExecutionContext(
            execution_config=ExecutionConfig(
                module_name="test_want_json",
                module_dirs=[test_modules_dir],
                module_args={"change": True},
            ),
            gate_config=GateConfig(),
        )

        result = await runner.run(localhost, context)

        assert result.is_success
        assert result.changed

    @pytest.mark.asyncio
    async def test_run_new_style_module(self, localhost: HostConfig, test_modules_dir: Path):
        """Test executing a new-style module."""
        runner = LocalModuleRunner()
        context = ExecutionContext(
            execution_config=ExecutionConfig(
                module_name="test_new_style",
                module_dirs=[test_modules_dir],
                module_args={"key1": "val1", "key2": "val2"},
            ),
            gate_config=GateConfig(),
        )

        result = await runner.run(localhost, context)

        assert result.is_success
        assert result.host_name == "localhost"
        assert result.output["msg"] == "New-style module executed"
        assert "received_args" in result.output
        assert result.output["received_args"]["key1"] == "val1"
        assert not result.changed

    @pytest.mark.asyncio
    async def test_run_new_style_module_with_change(
        self, localhost: HostConfig, test_modules_dir: Path
    ):
        """Test new-style module that reports changes."""
        runner = LocalModuleRunner()
        context = ExecutionContext(
            execution_config=ExecutionConfig(
                module_name="test_new_style",
                module_dirs=[test_modules_dir],
                module_args={"change": True, "data": "test"},
            ),
            gate_config=GateConfig(),
        )

        result = await runner.run(localhost, context)

        assert result.is_success
        assert result.changed
        assert result.output["received_args"]["data"] == "test"

    @pytest.mark.asyncio
    async def test_run_module_with_override_dirs(
        self, localhost: HostConfig, test_modules_dir: Path
    ):
        """Test executing a module with module_dirs_override."""
        runner = LocalModuleRunner()
        context = ExecutionContext(
            execution_config=ExecutionConfig(
                module_name="test_new_style",
                module_dirs=[Path("/nonexistent")],  # Wrong path
                module_args={"test": "override"},
            ),
            gate_config=GateConfig(),
            module_dirs_override=[str(test_modules_dir)],  # Override with correct path
        )

        result = await runner.run(localhost, context)

        assert result.is_success
        assert result.output["received_args"]["test"] == "override"
