# Example 1: Local Execution

This example demonstrates running FTL2 modules on the local machine without SSH connections.

## Overview

Local execution is the simplest mode - FTL2 runs modules directly on the same machine where the command is executed. This is useful for:
- Testing modules during development
- Running administrative tasks on a single machine
- Learning FTL2 basics without network complexity

## Prerequisites

- FTL2 installed (from parent directory)
- Python 3.11+ available

## Files

- `inventory.yml` - Inventory with localhost configuration
- `run_examples.sh` - Script with example commands

## Quick Start

```bash
# From this directory
./run_examples.sh
```

## Manual Examples

### 1. Ping Module (Test Connectivity)

```bash
# Basic ping to verify local execution works
ftl2 -m ping -i inventory.yml

# Expected output:
# localhost | SUCCESS => {
#     "changed": false,
#     "ping": "pong"
# }
```

### 2. Setup Module (Gather Facts)

```bash
# Gather system information
ftl2 -m setup -i inventory.yml

# Expected output: JSON with system facts (OS, memory, CPU, etc.)
```

### 3. File Module (Create File)

```bash
# Create a temporary file
ftl2 -m file -i inventory.yml -a "path=/tmp/ftl2-test state=touch"

# Verify the file was created
ls -la /tmp/ftl2-test

# Clean up
ftl2 -m file -i inventory.yml -a "path=/tmp/ftl2-test state=absent"
```

### 4. Shell Module (Run Commands)

```bash
# Execute a shell command
ftl2 -m shell -i inventory.yml -a "cmd='echo Hello from FTL2'"

# Expected output:
# localhost | SUCCESS => {
#     "changed": true,
#     "stdout": "Hello from FTL2",
#     "stderr": "",
#     "rc": 0
# }
```

### 5. Copy Module (Copy Files)

```bash
# Create a test file
echo "FTL2 Test Content" > /tmp/source.txt

# Copy it to a new location
ftl2 -m copy -i inventory.yml -a "src=/tmp/source.txt dest=/tmp/destination.txt"

# Verify
cat /tmp/destination.txt

# Clean up
rm /tmp/source.txt /tmp/destination.txt
```

## Understanding Local Execution

### How It Works

When using `ansible_connection: local` in the inventory:

1. FTL2 detects the connection type is "local"
2. Uses `LocalModuleRunner` instead of `RemoteModuleRunner`
3. Modules execute directly via subprocess (no SSH, no gate)
4. Results are returned immediately

### Connection Configuration

In `inventory.yml`:

```yaml
all:
  hosts:
    localhost:
      ansible_connection: local
      ansible_python_interpreter: /usr/bin/python3
```

Key fields:
- `ansible_connection: local` - Tells FTL2 to run locally
- `ansible_python_interpreter` - Python to use for module execution

### Advantages

- **Fast**: No network overhead
- **Simple**: No SSH setup required
- **Secure**: No credentials needed
- **Debuggable**: Easy to trace execution

### Limitations

- Only works on one machine
- Cannot manage remote systems
- Less realistic for testing distributed scenarios

## Next Steps

After mastering local execution, try:
- Example 02: Remote SSH execution with Docker
- Example 03: Multi-host deployments

## Troubleshooting

### "Module not found"

Make sure you're running from the examples directory or specify the full path:

```bash
cd examples/01-local-execution
ftl2 -m ping -i inventory.yml
```

### "Python interpreter not found"

Update `ansible_python_interpreter` in inventory.yml to match your system:

```bash
which python3  # Find your Python path
# Update inventory.yml with this path
```

### Permission Denied

Some operations require elevated privileges:

```bash
# This will fail without sudo
ftl2 -m file -i inventory.yml -a "path=/etc/test-file state=touch"

# Run with sudo if needed (not recommended for testing)
sudo ftl2 -m file -i inventory.yml -a "path=/tmp/test-file state=touch"
```
