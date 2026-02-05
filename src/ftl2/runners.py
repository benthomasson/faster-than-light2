"""Module runner interfaces and implementations for FTL2.

This module defines the strategy pattern for module execution, providing
pluggable runners for local and remote execution with a common interface.
"""

import asyncio
import json
import logging
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .types import ExecutionConfig, GateConfig, HostConfig, ModuleResult
from .utils import find_module, module_wants_json

logger = logging.getLogger(__name__)


@dataclass
class ExecutionContext:
    """Context for module execution operations.

    Bundles all configuration needed for executing modules across an
    inventory, reducing function parameters from 11 to 1.

    Attributes:
        execution_config: Module execution configuration
        gate_config: Gate building and caching configuration
        module_dirs_override: Optional override for module directories

    Example:
        >>> from pathlib import Path
        >>> exec_config = ExecutionConfig(
        ...     module_name="ping",
        ...     module_dirs=[Path("/usr/lib/ftl/modules")]
        ... )
        >>> gate_config = GateConfig()
        >>> context = ExecutionContext(
        ...     execution_config=exec_config,
        ...     gate_config=gate_config
        ... )
    """

    execution_config: ExecutionConfig
    gate_config: GateConfig
    module_dirs_override: list[str] = field(default_factory=list)

    @property
    def module_name(self) -> str:
        """Get the module name from execution config."""
        return self.execution_config.module_name

    @property
    def module_args(self) -> dict[str, Any]:
        """Get module arguments from execution config."""
        return self.execution_config.module_args


class ModuleRunner(ABC):
    """Abstract base class for module execution strategies.

    Defines the interface for executing modules on hosts, enabling
    pluggable execution strategies (local vs remote) with a common API.

    This follows the Strategy pattern, allowing runtime selection of
    execution method based on host configuration.
    """

    @abstractmethod
    async def run(
        self,
        host: HostConfig,
        context: ExecutionContext,
    ) -> ModuleResult:
        """Execute a module on a single host.

        Args:
            host: Host configuration for execution target
            context: Execution context with module and gate config

        Returns:
            ModuleResult containing execution outcome

        Raises:
            Exception: Various exceptions depending on implementation
        """
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up any resources held by this runner.

        Called when the runner is no longer needed. Implementations
        should close connections, release resources, etc.
        """
        pass


class ModuleRunnerFactory:
    """Factory for creating appropriate module runners.

    Selects the correct runner implementation based on host configuration,
    providing a unified interface for module execution.

    Example:
        >>> factory = ModuleRunnerFactory()
        >>> local_host = HostConfig(
        ...     name="localhost",
        ...     ansible_host="127.0.0.1",
        ...     ansible_connection="local"
        ... )
        >>> runner = factory.create_runner(local_host)
        >>> # Returns LocalModuleRunner
    """

    def __init__(self) -> None:
        """Initialize the factory."""
        self._local_runner: LocalModuleRunner | None = None
        self._remote_runner: RemoteModuleRunner | None = None

    def create_runner(self, host: HostConfig) -> ModuleRunner:
        """Create appropriate runner for the given host.

        Args:
            host: Host configuration to determine runner type

        Returns:
            ModuleRunner instance (Local or Remote)
        """
        if host.is_local:
            if self._local_runner is None:
                self._local_runner = LocalModuleRunner()
            return self._local_runner
        else:
            if self._remote_runner is None:
                self._remote_runner = RemoteModuleRunner()
            return self._remote_runner

    async def cleanup_all(self) -> None:
        """Clean up all created runners."""
        if self._local_runner:
            await self._local_runner.cleanup()
        if self._remote_runner:
            await self._remote_runner.cleanup()


class LocalModuleRunner(ModuleRunner):
    """Runner for executing modules locally without SSH.

    Executes modules directly on the local system using subprocess,
    bypassing SSH for improved performance on localhost operations.

    Example:
        >>> runner = LocalModuleRunner()
        >>> context = ExecutionContext(
        ...     execution_config=ExecutionConfig(module_name="ping"),
        ...     gate_config=GateConfig()
        ... )
        >>> host = HostConfig(
        ...     name="localhost",
        ...     ansible_host="127.0.0.1",
        ...     ansible_connection="local"
        ... )
        >>> result = await runner.run(host, context)
        >>> result.is_success
        True
    """

    async def run(
        self,
        host: HostConfig,
        context: ExecutionContext,
    ) -> ModuleResult:
        """Execute a module locally.

        Args:
            host: Host configuration (should be local)
            context: Execution context

        Returns:
            ModuleResult with execution outcome

        Raises:
            ModuleExecutionError: If execution fails
        """
        try:
            # Find the module
            module_dirs = context.execution_config.module_dirs
            if context.module_dirs_override:
                module_dirs = [Path(d) for d in context.module_dirs_override]

            module_path = find_module(module_dirs, context.module_name)
            if module_path is None:
                return ModuleResult.error_result(
                    host_name=host.name,
                    error=f"Module {context.module_name} not found in {module_dirs}",
                )

            # Execute the module based on its type
            # Python modules (.py extension) use JSON or new-style interface
            # Non-Python modules are treated as binary executables
            if module_path.suffix == ".py":
                if module_wants_json(module_path):
                    result_data = await self._run_json_module(module_path, context.module_args)
                else:
                    result_data = await self._run_new_style_module(module_path, context.module_args)
            else:
                # No .py extension - treat as binary executable
                result_data = await self._run_binary_module(module_path, context.module_args)

            # Parse the result
            if isinstance(result_data, dict):
                output = result_data
            else:
                try:
                    output = json.loads(result_data)
                except (json.JSONDecodeError, TypeError):
                    output = {"stdout": str(result_data)}

            # Determine if module made changes
            changed = output.get("changed", False)

            return ModuleResult.success_result(host_name=host.name, output=output, changed=changed)

        except Exception as e:
            logger.exception(f"Error executing module {context.module_name}")
            return ModuleResult.error_result(
                host_name=host.name, error=f"Execution failed: {str(e)}"
            )

    async def _run_binary_module(self, module_path: Path, module_args: dict[str, Any]) -> str:
        """Execute a binary module with command-line arguments.

        Args:
            module_path: Path to the binary module
            module_args: Arguments to pass as command-line args

        Returns:
            Module output as string
        """
        # Build command-line arguments
        args_str = " ".join(f"{k}={v}" for k, v in module_args.items())
        cmd = f"{module_path} {args_str}"

        # Execute the module
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await proc.communicate()
        return stdout.decode()

    async def _run_json_module(self, module_path: Path, module_args: dict[str, Any]) -> str:
        """Execute a module that wants JSON input via file.

        Args:
            module_path: Path to the module
            module_args: Arguments to pass as JSON file

        Returns:
            Module output as string
        """
        # Create temporary JSON args file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(module_args, f)
            args_file = f.name

        try:
            # Execute module with args file path
            cmd = f"python3 {module_path} {args_file}"
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            stdout, _ = await proc.communicate()
            return stdout.decode()
        finally:
            # Clean up temp file
            Path(args_file).unlink(missing_ok=True)

    async def _run_new_style_module(self, module_path: Path, module_args: dict[str, Any]) -> str:
        """Execute a new-style module with JSON stdin.

        Args:
            module_path: Path to the module
            module_args: Arguments to pass via stdin as JSON

        Returns:
            Module output as string
        """
        # Prepare JSON input
        json_input = json.dumps(module_args).encode()

        # Execute module with JSON stdin
        cmd = f"python3 {module_path}"
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await proc.communicate(json_input)
        return stdout.decode()

    async def cleanup(self) -> None:
        """Clean up local runner resources.

        Local runner has no persistent resources, so this is a no-op.
        """
        pass


class RemoteModuleRunner(ModuleRunner):
    """Runner for executing modules remotely via SSH gates.

    Manages SSH connections, gate processes, and remote module execution
    with connection pooling and caching for performance.

    Attributes:
        gate_cache: Cache of active gate connections by host

    Example:
        >>> runner = RemoteModuleRunner()
        >>> context = ExecutionContext(
        ...     execution_config=ExecutionConfig(module_name="ping"),
        ...     gate_config=GateConfig()
        ... )
        >>> host = HostConfig(
        ...     name="web01",
        ...     ansible_host="192.168.1.10"
        ... )
        >>> result = await runner.run(host, context)
    """

    def __init__(self) -> None:
        """Initialize the remote runner with empty gate cache."""
        self.gate_cache: dict[str, Any] = {}

    async def run(
        self,
        host: HostConfig,
        context: ExecutionContext,
    ) -> ModuleResult:
        """Execute a module remotely via SSH gate.

        Args:
            host: Remote host configuration
            context: Execution context

        Returns:
            ModuleResult with execution outcome

        Raises:
            NotImplementedError: Implementation pending
        """
        # TODO: Implement remote module execution via gates
        # This will be implemented after local runner
        raise NotImplementedError("Remote module execution not yet implemented")

    async def cleanup(self) -> None:
        """Clean up gate connections and resources.

        Closes all cached gate connections and clears the cache.
        """
        # TODO: Implement gate cleanup
        # Close all gates in gate_cache
        self.gate_cache.clear()
