"""Module loading for FTL2.

Provides functionality to load and execute Ansible modules with
better performance by separating bundle building from param passing.
"""

from ftl2.module_loading.fqcn import (
    parse_fqcn,
    get_collection_paths,
    resolve_fqcn,
    find_ansible_builtin_path,
    find_ansible_module_utils_path,
)
from ftl2.module_loading.dependencies import (
    find_module_utils_imports,
    find_module_utils_imports_from_file,
    find_all_dependencies,
    resolve_module_util_import,
    ModuleUtilsImport,
    DependencyResult,
)
from ftl2.module_loading.bundle import (
    build_bundle,
    build_bundle_from_fqcn,
    verify_bundle,
    list_bundle_contents,
    Bundle,
    BundleInfo,
    BundleCache,
)
from ftl2.module_loading.executor import (
    ExecutionResult,
    execute_local,
    execute_local_fqcn,
    execute_bundle_local,
    execute_remote,
    execute_remote_with_staging,
    stage_bundle_remote,
    get_module_utils_pythonpath,
    ModuleExecutor,
)

__all__ = [
    # FQCN parsing
    "parse_fqcn",
    "get_collection_paths",
    "resolve_fqcn",
    "find_ansible_builtin_path",
    "find_ansible_module_utils_path",
    # Dependency detection
    "find_module_utils_imports",
    "find_module_utils_imports_from_file",
    "find_all_dependencies",
    "resolve_module_util_import",
    "ModuleUtilsImport",
    "DependencyResult",
    # Bundle building
    "build_bundle",
    "build_bundle_from_fqcn",
    "verify_bundle",
    "list_bundle_contents",
    "Bundle",
    "BundleInfo",
    "BundleCache",
    # Execution
    "ExecutionResult",
    "execute_local",
    "execute_local_fqcn",
    "execute_bundle_local",
    "execute_remote",
    "execute_remote_with_staging",
    "stage_bundle_remote",
    "get_module_utils_pythonpath",
    "ModuleExecutor",
]
