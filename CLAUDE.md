# CLAUDE.md

## What This Is

FTL2 is a Python automation framework that runs Ansible modules in-process instead of as subprocesses. It provides an `async with automation()` context manager that gives Python scripts direct access to the entire Ansible module ecosystem.

## Project Structure

```
src/ftl2/
    automation/         # AutomationContext, ModuleProxy — the async with automation() API
        context.py      # Main context manager, execute(), secret_bindings, record
        proxy.py        # Host/group proxy for ftl.webservers.dnf() syntax
        __init__.py     # automation() wrapper function
    ftl_modules/        # FTL-native module implementations (in-process, no subprocess)
        http.py         # ftl_uri, ftl_get_url (httpx-based)
        executor.py     # ExecuteResult dataclass, FTL module dispatcher
        swap.py, pip.py # Other native modules
    ftl_gate/           # Remote execution gate (.pyz zipapp)
        __main__.py     # Gate-side: receives modules over stdin, executes, returns results
    state/              # State management
        state.py        # State class for .ftl2-state.json
        execution.py    # ExecutionState for CLI run tracking
    gate.py             # Gate builder — creates .pyz with baked-in modules
    runners.py          # SSH connection, gate deployment, remote module execution
    cli.py              # Click CLI (ftl2 command)
    ssh.py              # SSH host abstraction
    inventory.py        # Inventory loading (YAML)
    executor.py         # Legacy module executor
    builder.py          # ftl-gate-builder entry point
```

## Key Abstractions

- **AutomationContext** (`automation/context.py`) — the core. Manages inventory, secrets, module execution, state, and recording
- **ModuleProxy** (`automation/proxy.py`) — translates `ftl.webservers.dnf()` into `context.execute("dnf", hosts, params)`
- **Gate** (`gate.py` + `ftl_gate/`) — .pyz zipapp deployed to remote hosts for module execution
- **ExecuteResult** (`ftl_modules/executor.py`) — dataclass returned from every module call

## How Module Execution Works

1. Script calls `await ftl.webservers.dnf(name="nginx", state="present")`
2. ModuleProxy resolves `webservers` to a host group and `dnf` to a module name
3. AutomationContext injects secret_bindings, captures original params for audit
4. For local: module runs in-process via Ansible's module machinery
5. For remote: module is sent to the gate over SSH stdin, gate executes and returns result
6. Result is stored in `_results` list for audit recording

## Common Commands

```bash
# Run tests
pytest

# Run specific test
pytest tests/test_automation.py -v

# Lint
ruff check src/

# Format
ruff format src/

# Type check
mypy src/ftl2
```

## Important Patterns

### Secret bindings injection

In `context.py`, `execute()` and `_execute_on_host()` both:
1. Capture `original_params = params` before injection (for audit)
2. Call `_get_secret_bindings_for_module()` to match patterns
3. Merge secrets into params: `params = {**secret_injections, **params}`

### Gate building

`gate.py` builds a .pyz zipapp containing:
- Ansible module source code (resolved via `module_loading/`)
- FTL-native modules in `ftl_modules_baked/`
- The gate runtime (`ftl_gate/__main__.py`)

### State file

`.ftl2-state.json` tracks provisioned resources and dynamically added hosts. Written on every `state.add()` call for crash recovery.

## Dependencies

- `asyncssh` — SSH connections
- `httpx` — async HTTP (used by ftl_uri)
- `click` — CLI
- `pyyaml` — inventory parsing
- `jinja2` — template module
- `rich` — CLI output
- `ftl-module-utils` — Ansible module_utils extracted for standalone use
- `ftl-builtin-modules` — Ansible builtin modules extracted
