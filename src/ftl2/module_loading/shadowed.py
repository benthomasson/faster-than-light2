"""Registry of Ansible modules shadowed by native FTL2 implementations.

Some Ansible modules can be transparently replaced with native FTL2
implementations. This provides seamless Ansible knowledge transfer -
code written using Ansible patterns "just works" with FTL2's optimized
native methods.

When users call these modules, FTL2 silently redirects to the native
implementation with matching parameters.
"""

# Module name → method name on HostScopedProxy
SHADOWED_MODULES: dict[str, str] = {
    # wait_for_connection → wait_for_ssh
    "wait_for_connection": "wait_for_ssh",
    "ansible.builtin.wait_for_connection": "wait_for_ssh",
    # ping → ping
    "ping": "ping",
    "ansible.builtin.ping": "ping",
    # File transfer modules - these MUST be native because they read local files
    # and transfer to remote hosts. Ansible modules can't do this as they run
    # on the remote side and can't access the controller's filesystem.
    "copy": "copy",
    "ansible.builtin.copy": "copy",
    "template": "template",
    "ansible.builtin.template": "template",
    "fetch": "fetch",
    "ansible.builtin.fetch": "fetch",
}


def is_shadowed(module_name: str) -> bool:
    """Check if a module is shadowed by a native implementation.

    Args:
        module_name: Module name (short name or FQCN)

    Returns:
        True if the module has a native FTL2 implementation
    """
    return module_name in SHADOWED_MODULES


def get_native_method(module_name: str) -> str | None:
    """Get the native method name for a shadowed module.

    Args:
        module_name: Module name (short name or FQCN)

    Returns:
        Native method name, or None if not shadowed
    """
    return SHADOWED_MODULES.get(module_name)
