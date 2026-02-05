# Example 3: Multi-Host Execution

This example demonstrates running FTL2 modules across multiple remote hosts simultaneously, showing parallel execution and host grouping.

## Overview

Multi-host execution is where FTL2 shines - running the same operation across many systems at once. This example:
- Launches 3 SSH server containers (web01, web02, db01)
- Groups hosts by role (webservers, databases)
- Demonstrates parallel execution
- Shows targeting specific hosts or groups

## Prerequisites

- Docker or Colima running
- Docker Compose available
- FTL2 installed (from parent directory)
- Python 3.11+ available

## Files

- `docker-compose.yml` - Multi-container SSH environment
- `inventory.yml` - Multi-host inventory with groups
- `run_examples.sh` - Script with multi-host examples
- `setup.sh` - Helper to start/stop all containers

## Architecture

```
┌─────────────────┐
│  FTL2 Client    │
│  (localhost)    │
└────────┬────────┘
         │
         ├─────────────┐
         │             │
    SSH (2222)    SSH (2223)    SSH (2224)
         │             │             │
    ┌────▼────┐   ┌────▼────┐   ┌────▼────┐
    │  web01  │   │  web02  │   │  db01   │
    │  Alpine │   │  Alpine │   │  Alpine │
    └─────────┘   └─────────┘   └─────────┘
    [webservers]  [webservers]  [databases]
```

## Quick Start

```bash
# Start all SSH server containers
./setup.sh start

# Run the multi-host examples
./run_examples.sh

# Stop all containers
./setup.sh stop
```

## Manual Setup

### 1. Start All Containers

```bash
docker compose up -d

# Wait for containers to be ready
sleep 10

# Verify all containers are running
docker compose ps
```

### 2. Test Connections

```bash
# Test connection to web01
ssh -p 2222 testuser@localhost

# Test connection to web02
ssh -p 2223 testuser@localhost

# Test connection to db01
ssh -p 2224 testuser@localhost

# Password for all: testpass
```

### 3. Run Multi-Host Commands

```bash
# Ping all hosts
ftl2 -m ping -i inventory.yml

# Ping only webservers
ftl2 -m ping -i inventory.yml --limit webservers

# Ping only databases
ftl2 -m ping -i inventory.yml --limit databases

# Gather facts from all hosts
ftl2 -m setup -i inventory.yml

# Run command on all hosts
ftl2 -m shell -i inventory.yml -a "cmd='hostname'"
```

### 4. Cleanup

```bash
docker compose down
```

## Understanding Multi-Host Execution

### Inventory Structure

The inventory organizes hosts into groups:

```yaml
all:
  children:
    webservers:
      hosts:
        web01:
          ansible_host: 127.0.0.1
          ansible_port: 2222
        web02:
          ansible_host: 127.0.0.1
          ansible_port: 2223

    databases:
      hosts:
        db01:
          ansible_host: 127.0.0.1
          ansible_port: 2224
```

**Groups:**
- `all` - Contains all hosts
- `webservers` - Web server hosts (web01, web02)
- `databases` - Database hosts (db01)

**Built-in Groups:**
- `all` - Always available, contains every host
- `ungrouped` - Hosts not in any group

### Parallel Execution

FTL2 executes modules in parallel across hosts by default:

```bash
# Runs ping on all 3 hosts simultaneously
ftl2 -m ping -i inventory.yml

# FTL2 will:
# 1. Parse inventory (3 hosts found)
# 2. Build gate zipapp (shared by all hosts)
# 3. Connect to all hosts in parallel (3 SSH connections)
# 4. Upload gate to each host
# 5. Execute module on all hosts concurrently
# 6. Collect results as they complete
# 7. Display aggregated results
```

**Performance Benefits:**
- Operations complete in parallel, not sequentially
- Total time ≈ time of slowest host, not sum of all hosts
- Efficient resource utilization

### Targeting Hosts

**Run on all hosts:**
```bash
ftl2 -m ping -i inventory.yml
```

**Run on specific group:**
```bash
ftl2 -m ping -i inventory.yml --limit webservers
ftl2 -m ping -i inventory.yml --limit databases
```

**Run on specific host:**
```bash
ftl2 -m ping -i inventory.yml --limit web01
ftl2 -m ping -i inventory.yml --limit db01
```

**Run on multiple hosts (pattern):**
```bash
# Hosts matching pattern
ftl2 -m ping -i inventory.yml --limit "web*"

# Exclude hosts
ftl2 -m ping -i inventory.yml --limit "!db*"

# Comma-separated list
ftl2 -m ping -i inventory.yml --limit "web01,web02"
```

### Group Variables

Groups can have shared variables:

```yaml
webservers:
  vars:
    http_port: 80
    app_name: mywebapp
  hosts:
    web01: ...
    web02: ...

databases:
  vars:
    db_port: 5432
    db_name: production
  hosts:
    db01: ...
```

All hosts in a group inherit the group's variables.

### Variable Precedence

Variables are resolved in this order (last wins):

1. Group variables (from `groups.vars`)
2. Host variables (from `hosts.<hostname>.vars`)
3. Module arguments (from `-a` flag)

## Examples

### Basic Multi-Host Operations

```bash
# Ping all hosts
ftl2 -m ping -i inventory.yml

# Check hostname on all hosts
ftl2 -m shell -i inventory.yml -a "cmd='hostname'"

# Check uptime on all hosts
ftl2 -m shell -i inventory.yml -a "cmd='uptime'"

# Check disk space on all hosts
ftl2 -m shell -i inventory.yml -a "cmd='df -h'"
```

### Group-Specific Operations

```bash
# Configure webservers only
ftl2 -m shell -i inventory.yml --limit webservers -a "cmd='echo \"Web server configured\" > /tmp/role'"

# Configure databases only
ftl2 -m shell -i inventory.yml --limit databases -a "cmd='echo \"Database server configured\" > /tmp/role'"

# Verify role configuration
ftl2 -m shell -i inventory.yml -a "cmd='cat /tmp/role'"
```

### File Deployment

```bash
# Create a config file locally
cat > /tmp/app.conf <<EOF
[app]
name=myapp
version=1.0
environment=production
EOF

# Deploy to webservers only
ftl2 -m copy -i inventory.yml --limit webservers -a "src=/tmp/app.conf dest=/tmp/app.conf"

# Verify deployment
ftl2 -m shell -i inventory.yml --limit webservers -a "cmd='cat /tmp/app.conf'"

# Deploy different config to database
cat > /tmp/db.conf <<EOF
[database]
name=mydb
port=5432
EOF

ftl2 -m copy -i inventory.yml --limit databases -a "src=/tmp/db.conf dest=/tmp/db.conf"
```

### Selective Execution

```bash
# Run on first webserver only
ftl2 -m ping -i inventory.yml --limit web01

# Run on all webservers
ftl2 -m ping -i inventory.yml --limit webservers

# Run on all except database
ftl2 -m ping -i inventory.yml --limit "!databases"

# Run on specific hosts
ftl2 -m ping -i inventory.yml --limit "web01,db01"
```

### Gathering Information

```bash
# Get Python version from all hosts
ftl2 -m shell -i inventory.yml -a "cmd='python3 --version'"

# Get OS info from webservers
ftl2 -m shell -i inventory.yml --limit webservers -a "cmd='cat /etc/os-release'"

# Get memory info from all hosts
ftl2 -m shell -i inventory.yml -a "cmd='free -h'"

# List running processes on databases
ftl2 -m shell -i inventory.yml --limit databases -a "cmd='ps aux | head -10'"
```

## Common Patterns

### Rolling Updates

Update hosts one at a time to minimize downtime:

```bash
# Update web01
ftl2 -m shell -i inventory.yml --limit web01 -a "cmd='echo \"Updated\" > /tmp/version'"

# Verify web01
ftl2 -m shell -i inventory.yml --limit web01 -a "cmd='cat /tmp/version'"

# Update web02
ftl2 -m shell -i inventory.yml --limit web02 -a "cmd='echo \"Updated\" > /tmp/version'"

# Verify web02
ftl2 -m shell -i inventory.yml --limit web02 -a "cmd='cat /tmp/version'"
```

### Configuration Drift Detection

```bash
# Deploy baseline config
ftl2 -m copy -i inventory.yml -a "src=/tmp/baseline.conf dest=/tmp/current.conf"

# Later, check for changes
ftl2 -m shell -i inventory.yml -a "cmd='md5sum /tmp/current.conf'"
```

### Health Checks

```bash
# Quick health check of all hosts
ftl2 -m ping -i inventory.yml

# Detailed health check
ftl2 -m shell -i inventory.yml -a "cmd='uptime && free -h && df -h'"
```

## Docker Container Details

The example uses 3 identical SSH server containers:

| Container | Hostname | SSH Port | Group       |
|-----------|----------|----------|-------------|
| web01     | web01    | 2222     | webservers  |
| web02     | web02    | 2223     | webservers  |
| db01      | db01     | 2224     | databases   |

All containers:
- Use the same base image (linuxserver/openssh-server)
- Have the same credentials (testuser/testpass)
- Run Alpine Linux with Python 3
- Are isolated on a Docker network

## Troubleshooting

### Some Hosts Failing

```bash
# Check which containers are running
docker compose ps

# Start specific container
docker compose up -d web01

# Check logs for specific container
docker compose logs web01
```

### Connection Timeout on Specific Host

```bash
# Test SSH connection manually
ssh -p 2222 testuser@localhost  # web01
ssh -p 2223 testuser@localhost  # web02
ssh -p 2224 testuser@localhost  # db01

# Check if port is open
nc -zv localhost 2222
nc -zv localhost 2223
nc -zv localhost 2224
```

### Different Results Across Hosts

This is normal! Hosts may have:
- Different execution timing
- Different available resources
- Different state (files, processes)

Use FTL2's output to identify which host returned which result.

### Slow Parallel Execution

By default, FTL2 executes in parallel. If execution seems slow:

```bash
# Enable verbose logging to see timing
ftl2 -m ping -i inventory.yml -vvv

# Check host resources
docker stats
```

## Scaling Up

To test with more hosts:

1. **Edit docker-compose.yml** - Add more services
2. **Edit inventory.yml** - Add more hosts to groups
3. **Restart environment** - `./setup.sh restart`

Example adding web03:

```yaml
# docker-compose.yml
services:
  web03:
    image: lscr.io/linuxserver/openssh-server:latest
    container_name: ftl2-example-web03
    ports:
      - "2225:2222"
    environment:
      - PASSWORD_ACCESS=true
      - USER_PASSWORD=testpass
      - USER_NAME=testuser

# inventory.yml
webservers:
  hosts:
    web03:
      ansible_host: 127.0.0.1
      ansible_port: 2225
      ansible_user: testuser
      ansible_connection: ssh
      ansible_python_interpreter: /usr/bin/python3
      vars:
        ansible_password: testpass
```

## Best Practices

1. **Use Groups** - Organize hosts by role, location, or function
2. **Test Small First** - Use `--limit` to test on one host before running on all
3. **Monitor Progress** - Use `-v` flags for verbose output on large deployments
4. **Handle Failures** - Some hosts may fail; FTL2 will continue with others
5. **Verify Results** - Always check output to ensure operations succeeded
6. **Use Idempotent Modules** - Prefer modules that are safe to run multiple times

## Next Steps

- Scale this example to more hosts
- Practice with different module types
- Experiment with group variables
- Build a real deployment workflow
- Explore failure handling and retries

## Security Notes

This example uses:
- Password authentication (not recommended for production)
- Same credentials for all hosts (never do this in production)
- No host key verification (dangerous in production)

For production:
- Use unique SSH keys per host
- Enable host key verification
- Use SSH bastion/jump hosts
- Implement role-based access control
- Rotate credentials regularly
- Use secrets management (Vault, etc.)
