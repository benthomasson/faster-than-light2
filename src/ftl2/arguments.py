"""Argument merging and resolution for module execution.

This module provides argument handling logic that combines base module arguments
with host-specific overrides, resolving any variable references in the process.

Key Features:
- Merge base module arguments with host-specific overrides
- Resolve Ref objects against host data
- Precedence: host_args > dereferenced refs > literals
- Type-safe with dataclasses
"""

from dataclasses import dataclass, field
from typing import Any

from ftl2.refs import Ref, deref
from ftl2.types import HostConfig


@dataclass
class ArgumentConfig:
    """Configuration for module argument handling.

    Attributes:
        module_args: Base arguments to pass to all modules. Can contain Ref
            objects for dynamic variable resolution.
        host_args: Mapping of host names to host-specific argument overrides.
            These have higher precedence than module_args.
    """

    module_args: dict[str, Any] = field(default_factory=dict)
    host_args: dict[str, dict[str, Any]] = field(default_factory=dict)


def has_refs(args: dict[str, Any] | None) -> bool:
    """Check if an argument dictionary contains any Ref objects.

    Args:
        args: Dictionary to check for Ref objects

    Returns:
        True if any value in the dictionary is a Ref object

    Example:
        >>> config = Ref(None, "config")
        >>> has_refs({"src": "/tmp", "dest": "/var"})
        False
        >>> has_refs({"src": config.src_dir, "dest": "/var"})
        True
    """
    if not args:
        return False

    return any(isinstance(value, Ref) for value in args.values())


def merge_arguments(
    host: HostConfig,
    module_args: dict[str, Any] | None,
    host_args: dict[str, dict[str, Any]] | None,
) -> dict[str, Any]:
    """Merge module arguments with host-specific overrides.

    This function implements the argument merging logic with proper precedence:
    1. host_args (highest precedence)
    2. dereferenced refs from module_args
    3. literal values from module_args

    Args:
        host: Host configuration to use for dereferencing
        module_args: Base arguments for all hosts
        host_args: Host-specific argument overrides

    Returns:
        Merged and resolved argument dictionary

    Example:
        >>> host = HostConfig(
        ...     name="web1",
        ...     ansible_host="192.168.1.100",
        ...     config={"src_dir": "/opt/app"}
        ... )
        >>> config = Ref(None, "config")
        >>> module_args = {"src": config.src_dir, "mode": "0755"}
        >>> host_args = {"web1": {"dest": "/var/app"}}
        >>> merge_arguments(host, module_args, host_args)
        {'src': '/opt/app', 'mode': '0755', 'dest': '/var/app'}
    """
    # Get host-specific overrides for this host
    host_specific_args = {}
    if host_args:
        host_specific_args = host_args.get(host.name, {})

    # Check if we need to do any merging
    has_refs_in_args = has_refs(module_args)

    # Fast path: no host-specific args and no refs
    if not host_specific_args and not has_refs_in_args:
        return module_args or {}

    # Slow path: need to merge and/or resolve refs
    merged_args = {}

    # Start with module_args (if any)
    if module_args:
        merged_args = module_args.copy()

        # Resolve any refs (refs have lower precedence than host-specific args)
        if has_refs_in_args:
            for arg_name, arg_value in module_args.items():
                merged_args[arg_name] = deref(host.vars, arg_value)

    # Apply host-specific args (higher precedence)
    merged_args.update(host_specific_args)

    return merged_args
