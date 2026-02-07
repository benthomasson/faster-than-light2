"""Module proxy for dynamic attribute access.

Enables the ftl.module_name() syntax by intercepting attribute access
and returning async wrappers for module functions.

Supports both simple modules and FQCN (Fully Qualified Collection Name):
    await ftl.file(path="/tmp/test", state="touch")
    await ftl.amazon.aws.ec2_instance(instance_type="t3.micro")
"""

from typing import Any, Callable, TYPE_CHECKING

from ftl2.module_loading.excluded import get_excluded
from ftl2.module_loading.shadowed import is_shadowed, get_native_method
from ftl2.exceptions import ExcludedModuleError

if TYPE_CHECKING:
    from ftl2.automation.context import AutomationContext


def _check_excluded(module_path: str) -> None:
    """Check if a module is excluded and raise if so.

    Args:
        module_path: Module name or FQCN

    Raises:
        ExcludedModuleError: If the module is excluded
    """
    excluded = get_excluded(module_path)
    if excluded:
        raise ExcludedModuleError(excluded)


class HostScopedProxy:
    """Proxy that runs modules on a specific host or group.

    Enables syntax like ftl.webservers.service(...) which is equivalent to
    ftl.run_on("webservers", "service", ...).

    Example:
        ftl.webservers.service(name="nginx", state="restarted")
        ftl.web01.file(path="/tmp/test", state="touch")
        ftl.local.community.general.linode_v4(label="web01", ...)
    """

    def __init__(self, context: "AutomationContext", target: str):
        """Initialize the host-scoped proxy.

        Args:
            context: The AutomationContext that handles execution
            target: Host name or group name to target
        """
        self._context = context
        self._target = target

    async def wait_for_ssh(
        self,
        timeout: int = 600,
        delay: int = 0,
        sleep: int = 1,
        connect_timeout: int = 5,
    ) -> dict[str, Any]:
        """Wait for SSH to become available on this host.

        This is the FTL2-native implementation that shadows Ansible's
        wait_for_connection module. Uses the same parameters for seamless
        Ansible knowledge transfer.

        Args:
            timeout: Maximum seconds to wait (default: 600, matches Ansible)
            delay: Seconds to wait before first check (default: 0)
            sleep: Seconds between retry attempts (default: 1)
            connect_timeout: Timeout for each connection attempt (default: 5)

        Returns:
            dict with 'elapsed' (seconds waited) and 'changed' (always False)

        Raises:
            TimeoutError: If SSH is not available within the timeout

        Example:
            ftl.add_host("minecraft-9", ansible_host=ip)
            await ftl.minecraft_9.wait_for_ssh(timeout=120, delay=10)
            await ftl.minecraft_9.dnf(name="java-17-openjdk")
        """
        import asyncio
        import time

        # Initial delay before first check
        if delay > 0:
            await asyncio.sleep(delay)

        # Get host info from inventory
        # hosts_proxy[host] returns list[HostConfig]
        hosts_proxy = self._context.hosts
        ansible_host = self._target
        port = 22

        if self._target in hosts_proxy.keys():
            host_configs = hosts_proxy[self._target]
            if host_configs:
                # Use the first matching host
                host_config = host_configs[0]
                ansible_host = host_config.ansible_host or self._target
                port = host_config.ansible_port or 22

        start = time.monotonic()
        last_error = None

        while True:
            try:
                # Try TCP connection to SSH port
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(ansible_host, port),
                    timeout=connect_timeout,
                )
                writer.close()
                await writer.wait_closed()
                elapsed = int(time.monotonic() - start)
                return {"elapsed": elapsed, "changed": False}
            except (OSError, asyncio.TimeoutError) as e:
                last_error = e
                elapsed = time.monotonic() - start
                if elapsed >= timeout:
                    raise TimeoutError(
                        f"SSH not available on {ansible_host}:{port} "
                        f"after {timeout} seconds"
                    ) from last_error
                await asyncio.sleep(sleep)

    async def ping(self) -> dict[str, str]:
        """Test FTL2 gate connectivity by executing through the full pipeline.

        This is the FTL2-native implementation that shadows Ansible's
        ping module. Unlike Ansible's ping (which tests connection plugin),
        this tests the complete FTL2 execution pipeline:

        1. TCP - Port reachable
        2. SSH - Authentication works
        3. Gate setup - Remote gate process starts (for remote hosts)
        4. Command execution - Can run commands through gate
        5. Response - Round-trip communication works

        The "pong" response is generated by actually executing a command
        on the target, proving the entire pipeline works.

        Returns:
            dict with {"ping": "pong"} - "pong" comes from the remote host

        Raises:
            ConnectionError: If connection fails
            AuthenticationError: If SSH auth fails
            TimeoutError: If connection times out

        Example:
            result = await ftl.minecraft.ping()
            assert result["ping"] == "pong"
        """
        from ftl2.exceptions import ConnectionError as FTL2ConnectionError

        try:
            # For local/localhost, use local execution
            if self._target in ("local", "localhost"):
                result = await self._context.execute("command", {"cmd": "echo pong"})
            else:
                # For remote hosts, run through the full gate pipeline
                results = await self._context.run_on(self._target, "command", cmd="echo pong")
                if not results:
                    raise FTL2ConnectionError(
                        f"Ping failed: no response from {self._target}"
                    )
                result = results[0]

                if not result.success:
                    raise FTL2ConnectionError(
                        f"Ping failed on {self._target}: {result.error}"
                    )

                # Extract output from ExecuteResult
                result = result.output

            # Verify we got the expected response
            stdout = result.get("stdout", "").strip()
            if stdout == "pong":
                return {"ping": "pong"}
            else:
                raise FTL2ConnectionError(
                    f"Ping failed: unexpected response '{stdout}'"
                )

        except TimeoutError:
            raise
        except FTL2ConnectionError:
            raise
        except Exception as e:
            raise FTL2ConnectionError(f"Ping failed: {e}") from e

    def __getattr__(self, name: str) -> "HostScopedModuleProxy":
        """Return a module proxy scoped to this host/group.

        Args:
            name: Module name or namespace component

        Returns:
            HostScopedModuleProxy for the module
        """
        if name.startswith("_"):
            raise AttributeError(name)

        return HostScopedModuleProxy(self._context, self._target, name)

    def __repr__(self) -> str:
        return f"HostScopedProxy({self._target!r})"


class HostScopedModuleProxy:
    """Proxy for a module scoped to a specific host/group.

    Supports both simple modules and FQCN:
        ftl.webservers.service(...)
        ftl.webservers.ansible.posix.firewalld(...)
    """

    def __init__(self, context: "AutomationContext", target: str, path: str):
        """Initialize the host-scoped module proxy.

        Args:
            context: The AutomationContext that handles execution
            target: Host name or group name to target
            path: Module name or namespace path
        """
        self._context = context
        self._target = target
        self._path = path

    def __getattr__(self, name: str) -> "HostScopedModuleProxy":
        """Extend the module path for FQCN support.

        Args:
            name: Next component of the namespace

        Returns:
            HostScopedModuleProxy with extended path
        """
        if name.startswith("_"):
            raise AttributeError(name)

        new_path = f"{self._path}.{name}"
        return HostScopedModuleProxy(self._context, self._target, new_path)

    async def __call__(self, **kwargs: Any) -> Any:
        """Execute the module on the target host/group.

        Args:
            **kwargs: Module parameters

        Returns:
            For localhost: dict (module output) - more intuitive for local use
            For remote hosts/groups: list[ExecuteResult]

        Raises:
            ExcludedModuleError: If the module is excluded from FTL2
        """
        # Check if module is shadowed by a native implementation
        if is_shadowed(self._path):
            method_name = get_native_method(self._path)
            host_proxy = HostScopedProxy(self._context, self._target)
            native_method = getattr(host_proxy, method_name)
            return await native_method(**kwargs)

        # Check if module is excluded
        _check_excluded(self._path)

        # Special case: local/localhost executes directly without inventory
        if self._target in ("local", "localhost"):
            return await self._context.execute(self._path, kwargs)

        return await self._context.run_on(self._target, self._path, **kwargs)

    def __repr__(self) -> str:
        return f"HostScopedModuleProxy({self._target!r}, {self._path!r})"


class NamespaceProxy:
    """Proxy for FQCN namespace traversal.

    Enables dotted access like ftl.amazon.aws.ec2_instance by tracking
    the namespace path and returning nested proxies until the final
    module is called.

    Example:
        ftl.amazon        -> NamespaceProxy(context, "amazon")
        ftl.amazon.aws    -> NamespaceProxy(context, "amazon.aws")
        ftl.amazon.aws.ec2_instance(...) -> executes "amazon.aws.ec2_instance"
    """

    def __init__(self, context: "AutomationContext", path: str):
        """Initialize the namespace proxy.

        Args:
            context: The AutomationContext that handles execution
            path: The current namespace path (e.g., "amazon" or "amazon.aws")
        """
        self._context = context
        self._path = path

    def __getattr__(self, name: str) -> "NamespaceProxy":
        """Return a nested proxy for the next namespace component.

        Args:
            name: Next component of the namespace

        Returns:
            NamespaceProxy with extended path
        """
        if name.startswith("_"):
            raise AttributeError(name)

        # Extend the path
        new_path = f"{self._path}.{name}"
        return NamespaceProxy(self._context, new_path)

    async def __call__(self, **kwargs: Any) -> dict[str, Any]:
        """Execute the module at the current path.

        This is called when the namespace proxy is invoked as a function,
        e.g., ftl.amazon.aws.ec2_instance(instance_type="t3.micro")

        Args:
            **kwargs: Module parameters

        Returns:
            Module output dictionary

        Raises:
            ExcludedModuleError: If the module is excluded from FTL2
        """
        # Check if module is excluded
        _check_excluded(self._path)

        return await self._context.execute(self._path, kwargs)

    def __repr__(self) -> str:
        return f"NamespaceProxy({self._path!r})"


class ModuleProxy:
    """Proxy that enables ftl.module_name() syntax via __getattr__.

    When you access an attribute like `ftl.file`, this proxy intercepts
    the access and returns an async wrapper that calls the FTL module.

    For simple modules (file, copy, command), it returns a callable wrapper.
    For namespaced modules (amazon.aws.ec2_instance), it returns a
    NamespaceProxy that enables chained attribute access.

    Example:
        proxy = ModuleProxy(context)

        # Simple module
        result = await proxy.file(path="/tmp/test", state="touch")

        # FQCN module (collection)
        result = await proxy.amazon.aws.ec2_instance(instance_type="t3.micro")
    """

    def __init__(self, context: "AutomationContext"):
        """Initialize the proxy with an automation context.

        Args:
            context: The AutomationContext that handles execution
        """
        self._context = context

    def __getattr__(self, name: str) -> Callable[..., Any] | NamespaceProxy | HostScopedProxy:
        """Return async wrapper for module, host proxy, or namespace proxy.

        Priority:
        1. local/localhost -> HostScopedProxy for localhost
        2. Host/group names -> HostScopedProxy for that target
        3. Known modules -> async wrapper
        4. Unknown names -> NamespaceProxy for FQCN

        Args:
            name: Module name, host/group name, or namespace

        Returns:
            Async function for known modules, HostScopedProxy for hosts/groups,
            NamespaceProxy for collection namespaces

        Raises:
            AttributeError: For private attributes or disabled modules
        """
        # Don't intercept private attributes
        if name.startswith("_"):
            raise AttributeError(name)

        # Check for local/localhost first
        if name in ("local", "localhost"):
            return HostScopedProxy(self._context, "localhost")

        # Check if it's a host or group name
        # Also check with underscore→dash normalization since Python attributes
        # can't have dashes but hostnames commonly do (DNS standard)
        try:
            hosts_proxy = self._context.hosts
            # Try exact match first
            if name in hosts_proxy.groups or name in hosts_proxy.keys():
                return HostScopedProxy(self._context, name)
            # Try underscore→dash normalization (e.g., minecraft_9 → minecraft-9)
            normalized = name.replace("_", "-")
            if normalized != name:
                if normalized in hosts_proxy.groups or normalized in hosts_proxy.keys():
                    return HostScopedProxy(self._context, normalized)
        except Exception:
            # Inventory not loaded or other issue - continue to module check
            pass

        # Check if it's a known simple module
        from ftl2.ftl_modules import get_module, list_modules

        module = get_module(name)
        if module is not None:
            # Known module - return async wrapper
            async def wrapper(**kwargs: Any) -> dict[str, Any]:
                """Execute the module with the given parameters."""
                # Check if module is excluded
                _check_excluded(name)
                return await self._context.execute(name, kwargs)

            wrapper.__name__ = name
            wrapper.__doc__ = f"Execute the '{name}' module."
            return wrapper

        # Check if it's in the enabled modules list (if restricted)
        if self._context._enabled_modules is not None:
            if name in list_modules():
                raise AttributeError(
                    f"Module '{name}' is not enabled. "
                    f"Enabled modules: {', '.join(self._context._enabled_modules)}"
                )

        # Not a known simple module - treat as namespace for FQCN
        # This enables: ftl.amazon.aws.ec2_instance(...)
        return NamespaceProxy(self._context, name)
