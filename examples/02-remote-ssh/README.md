# Example 2: Remote SSH Execution

This example demonstrates running FTL2 modules on a remote machine via SSH using a Docker container as the target host.

## Overview

Remote execution is FTL2's primary use case - running modules on remote systems via SSH. This example:
- Launches an SSH server in a Docker container
- Configures FTL2 to connect via SSH
- Demonstrates the same modules as Example 01, but remotely

## Prerequisites

- Docker or Colima running
- Docker Compose available
- FTL2 installed (from parent directory)
- Python 3.11+ available

## Files

- `docker-compose.yml` - SSH server container configuration
- `inventory.yml` - Inventory with remote SSH host
- `run_examples.sh` - Script with example commands
- `setup.sh` - Helper to start/stop the SSH container

## Quick Start

```bash
# Start the SSH server container
./setup.sh start

# Run the examples
./run_examples.sh

# Stop the SSH server container
./setup.sh stop
```

## Manual Setup

### 1. Start SSH Server Container

```bash
docker compose up -d

# Wait for container to be ready
sleep 5

# Verify container is running
docker compose ps
```

### 2. Test SSH Connection

```bash
# Test manual SSH connection
ssh -p 2222 -o StrictHostKeyChecking=no testuser@localhost

# Password: testpass
# You should get a shell prompt
```

### 3. Run FTL2 Commands

```bash
# Ping the remote host
ftl2 -m ping -i inventory.yml

# Gather facts from remote host
ftl2 -m setup -i inventory.yml

# Create a file on the remote host
ftl2 -m file -i inventory.yml -a "path=/tmp/remote-test state=touch"

# Verify the file exists in the container
docker compose exec remote-server ls -la /tmp/remote-test

# Run a shell command remotely
ftl2 -m shell -i inventory.yml -a "cmd='uname -a'"
```

### 4. Cleanup

```bash
docker compose down
```

## Understanding Remote Execution

### How It Works

When using `ansible_connection: ssh` in the inventory:

1. FTL2 detects SSH connection type
2. Uses `RemoteModuleRunner` with asyncssh library
3. Builds a gate zipapp containing the module
4. Connects to remote host via SSH
5. Uploads gate to /tmp/ on remote host
6. Executes gate with Python interpreter
7. Gate runs the module and returns results
8. Connection is closed and results displayed

### Connection Configuration

In `inventory.yml`:

```yaml
all:
  hosts:
    remote-server:
      ansible_host: 127.0.0.1
      ansible_port: 2222
      ansible_user: testuser
      ansible_connection: ssh
      ansible_python_interpreter: /usr/bin/python3
      vars:
        ansible_password: testpass
```

Key fields:
- `ansible_host` - IP address or hostname
- `ansible_port` - SSH port (default 22, here 2222 for Docker)
- `ansible_user` - SSH username
- `ansible_connection: ssh` - Enables remote execution
- `ansible_python_interpreter` - Python path on remote host
- `vars.ansible_password` - Password authentication (not recommended for production)

### SSH Authentication Methods

**Password Authentication (This Example):**
```yaml
vars:
  ansible_password: testpass
```

**SSH Key Authentication (Recommended for Production):**
```yaml
# No password needed if SSH keys are configured
# FTL2 will use your default SSH key (~/.ssh/id_rsa)
```

To set up SSH keys:
```bash
# Generate SSH key if you don't have one
ssh-keygen -t rsa -b 4096

# Copy public key to remote host
ssh-copy-id -p 2222 testuser@localhost
```

### Gate Mechanism

The "gate" is a zipapp that FTL2 creates for each module execution:

1. **Building**: FTL2 packages the module code into a Python zipapp
2. **Caching**: Gates are cached by content hash for reuse
3. **Upload**: Gate is copied to remote host's /tmp directory
4. **Execution**: Python interpreter runs the gate
5. **Protocol**: Gate communicates via length-prefixed JSON
6. **Cleanup**: Gate remains in /tmp for cache reuse

You can inspect gates:
```bash
# List cached gates
ls -la /tmp/ftl_gate_*.pyz

# Test a gate manually
echo -n '0000000d["Hello", {}]' | python3 /tmp/ftl_gate_*.pyz
```

## Docker Container Details

The SSH server container (`linuxserver/openssh-server`):

- **Base Image**: Alpine Linux with OpenSSH
- **SSH Port**: 2222 (mapped to host 2222)
- **Username**: testuser
- **Password**: testpass
- **Python**: Installed via Alpine package manager
- **Access**: Password authentication enabled

Container environment variables:
```yaml
environment:
  - PASSWORD_ACCESS=true
  - USER_PASSWORD=testpass
  - USER_NAME=testuser
```

## Examples

### Basic Operations

```bash
# Test connectivity
ftl2 -m ping -i inventory.yml

# Gather system information
ftl2 -m setup -i inventory.yml

# Check disk space
ftl2 -m shell -i inventory.yml -a "cmd='df -h'"
```

### File Management

```bash
# Create a file
ftl2 -m file -i inventory.yml -a "path=/tmp/test.txt state=touch"

# Create a directory
ftl2 -m file -i inventory.yml -a "path=/tmp/mydir state=directory mode=0755"

# Copy a local file to remote
echo "Hello Remote" > /tmp/local-file.txt
ftl2 -m copy -i inventory.yml -a "src=/tmp/local-file.txt dest=/tmp/remote-file.txt"

# Verify the file on remote
ftl2 -m shell -i inventory.yml -a "cmd='cat /tmp/remote-file.txt'"

# Remove files
ftl2 -m file -i inventory.yml -a "path=/tmp/test.txt state=absent"
ftl2 -m file -i inventory.yml -a "path=/tmp/mydir state=absent"
```

### Running Commands

```bash
# Check OS version
ftl2 -m shell -i inventory.yml -a "cmd='cat /etc/os-release'"

# Check Python version
ftl2 -m shell -i inventory.yml -a "cmd='python3 --version'"

# List processes
ftl2 -m shell -i inventory.yml -a "cmd='ps aux'"

# Check network configuration
ftl2 -m shell -i inventory.yml -a "cmd='ip addr show'"
```

## Troubleshooting

### Container Not Starting

```bash
# Check if Colima is running (macOS)
colima status

# Start Colima if needed
colima start

# Check Docker Compose logs
docker compose logs remote-server
```

### SSH Connection Refused

```bash
# Wait a few seconds for the container to initialize
sleep 5

# Check if container is running
docker compose ps

# Check SSH is listening
docker compose exec remote-server netstat -tuln | grep 2222
```

### Authentication Failed

```bash
# Verify credentials in inventory.yml match docker-compose.yml
# Username: testuser
# Password: testpass

# Test manual SSH connection
ssh -p 2222 testuser@localhost
```

### "Python interpreter not found" on Remote

```bash
# Verify Python is installed in container
docker compose exec remote-server which python3

# If missing, install it
docker compose exec remote-server apk add python3

# Update inventory.yml with correct path
ansible_python_interpreter: /usr/bin/python3
```

### Gate Execution Failures

```bash
# Enable verbose logging
ftl2 -m ping -i inventory.yml -vvv

# Check remote /tmp for gates
docker compose exec remote-server ls -la /tmp/ftl_gate_*.pyz

# Test gate manually
docker compose exec remote-server sh -c 'echo -n "0000000d[\"Hello\", {}]" | python3 /tmp/ftl_gate_*.pyz'
```

## Next Steps

After mastering remote SSH execution, try:
- Example 03: Multi-host deployments with multiple SSH servers
- Modify docker-compose.yml to add more containers
- Practice with different modules and arguments

## Security Notes

**For Production Use:**

1. **Never use password authentication** - use SSH keys instead
2. **Disable StrictHostKeyChecking carefully** - verify host keys in production
3. **Use SSH agent forwarding** for key management
4. **Rotate credentials regularly**
5. **Use SSH bastion hosts** for accessing internal networks
6. **Enable SSH audit logging** on remote hosts
7. **Use per-host credentials** instead of shared passwords

This example uses password authentication and disabled host key checking for simplicity. Do not use this configuration in production environments.
