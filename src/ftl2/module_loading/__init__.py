"""Module loading for FTL2.

Provides functionality to load and execute Ansible modules with
better performance by separating bundle building from param passing.
"""

from ftl2.module_loading.fqcn import (
    parse_fqcn,
    get_collection_paths,
    resolve_fqcn,
    find_ansible_builtin_path,
)

__all__ = [
    "parse_fqcn",
    "get_collection_paths",
    "resolve_fqcn",
    "find_ansible_builtin_path",
]
