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
from ftl2.module_loading.dependencies import (
    find_module_utils_imports,
    find_module_utils_imports_from_file,
    find_all_dependencies,
    resolve_module_util_import,
    ModuleUtilsImport,
    DependencyResult,
)

__all__ = [
    # FQCN parsing
    "parse_fqcn",
    "get_collection_paths",
    "resolve_fqcn",
    "find_ansible_builtin_path",
    # Dependency detection
    "find_module_utils_imports",
    "find_module_utils_imports_from_file",
    "find_all_dependencies",
    "resolve_module_util_import",
    "ModuleUtilsImport",
    "DependencyResult",
]
