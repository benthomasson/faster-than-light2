#!/bin/bash
# FTL2 Remote SSH Execution Examples
# This script demonstrates various FTL2 modules running remotely via SSH

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "======================================"
echo "FTL2 Remote SSH Execution Examples"
echo "======================================"
echo

# Check if ftl2 is available
if ! command -v ftl2 &> /dev/null; then
    echo -e "${RED}Error: ftl2 not found in PATH${NC}"
    echo "Please install ftl2 or activate your virtual environment"
    echo
    echo "From the project root:"
    echo "  source .venv/bin/activate"
    echo "  pip install -e ."
    exit 1
fi

# Check if Docker container is running
if ! docker compose ps | grep -q "Up"; then
    echo -e "${YELLOW}Warning: SSH server container is not running${NC}"
    echo "Starting the container now..."
    echo
    ./setup.sh start
    echo
fi

echo -e "${GREEN}Using ftl2:${NC} $(which ftl2)"
echo -e "${GREEN}Target host:${NC} remote-server (127.0.0.1:2222)"
echo

# Example 1: Ping Module
echo "1. Testing remote connectivity with ping module..."
echo "   Command: ftl2 -m ping -i inventory.yml"
echo
ftl2 -m ping -i inventory.yml
echo

# Example 2: Setup Module (limited output)
echo "2. Gathering remote system facts with setup module..."
echo "   Command: ftl2 -m setup -i inventory.yml"
echo
ftl2 -m setup -i inventory.yml | head -25
echo "   (output truncated - full facts available)"
echo

# Example 3: Shell Module - System Info
echo "3. Checking remote OS version..."
echo "   Command: ftl2 -m shell -i inventory.yml -a \"cmd='cat /etc/os-release'\""
echo
ftl2 -m shell -i inventory.yml -a "cmd='cat /etc/os-release'"
echo

# Example 4: File Module - Create
echo "4. Creating a test file on remote host..."
echo "   Command: ftl2 -m file -i inventory.yml -a \"path=/tmp/ftl2-remote-test.txt state=touch\""
echo
ftl2 -m file -i inventory.yml -a "path=/tmp/ftl2-remote-test.txt state=touch"
echo
echo "   Verifying file exists in container:"
docker compose exec -T remote-server ls -la /tmp/ftl2-remote-test.txt
echo

# Example 5: Shell Module - Python Version
echo "5. Checking remote Python version..."
echo "   Command: ftl2 -m shell -i inventory.yml -a \"cmd='python3 --version'\""
echo
ftl2 -m shell -i inventory.yml -a "cmd='python3 --version'"
echo

# Example 6: Copy Module
echo "6. Copying a file to remote host..."
echo "   Creating local source file..."
echo "FTL2 Remote Example Content - $(date)" > /tmp/ftl2-local-source.txt
echo "   Command: ftl2 -m copy -i inventory.yml -a \"src=/tmp/ftl2-local-source.txt dest=/tmp/ftl2-remote-copy.txt\""
echo
ftl2 -m copy -i inventory.yml -a "src=/tmp/ftl2-local-source.txt dest=/tmp/ftl2-remote-copy.txt"
echo
echo "   Verifying copied file content:"
ftl2 -m shell -i inventory.yml -a "cmd='cat /tmp/ftl2-remote-copy.txt'"
echo

# Example 7: Shell Module - Disk Space
echo "7. Checking remote disk space..."
echo "   Command: ftl2 -m shell -i inventory.yml -a \"cmd='df -h'\""
echo
ftl2 -m shell -i inventory.yml -a "cmd='df -h'"
echo

# Example 8: File Module - Create Directory
echo "8. Creating a directory on remote host..."
echo "   Command: ftl2 -m file -i inventory.yml -a \"path=/tmp/ftl2-testdir state=directory mode=0755\""
echo
ftl2 -m file -i inventory.yml -a "path=/tmp/ftl2-testdir state=directory mode=0755"
echo
echo "   Verifying directory exists:"
docker compose exec -T remote-server ls -lad /tmp/ftl2-testdir
echo

# Example 9: Shell Module - List /tmp
echo "9. Listing /tmp directory on remote host..."
echo "   Command: ftl2 -m shell -i inventory.yml -a \"cmd='ls -la /tmp/ftl2*'\""
echo
ftl2 -m shell -i inventory.yml -a "cmd='ls -la /tmp/ftl2*'"
echo

# Example 10: Cleanup
echo "10. Cleaning up test files and directories..."
echo "    Removing /tmp/ftl2-remote-test.txt"
ftl2 -m file -i inventory.yml -a "path=/tmp/ftl2-remote-test.txt state=absent"
echo "    Removing /tmp/ftl2-remote-copy.txt"
ftl2 -m file -i inventory.yml -a "path=/tmp/ftl2-remote-copy.txt state=absent"
echo "    Removing /tmp/ftl2-testdir"
ftl2 -m file -i inventory.yml -a "path=/tmp/ftl2-testdir state=absent"
echo "    Removing local source file"
rm -f /tmp/ftl2-local-source.txt
echo

echo "======================================"
echo "All remote examples completed!"
echo "======================================"
echo
echo "Key observations:"
echo "  - All operations executed on remote-server (Docker container)"
echo "  - FTL2 used SSH to connect (port 2222)"
echo "  - Gate zipapp uploaded and executed remotely"
echo "  - Results returned and displayed locally"
echo
echo "Next steps:"
echo "  - Review the output to understand remote execution"
echo "  - Check the README.md for detailed explanations"
echo "  - Inspect gates in /tmp: ls -la /tmp/ftl_gate_*.pyz"
echo "  - Try example 03-multi-host for multi-host deployments"
echo
echo "Stop the SSH container:"
echo "  ./setup.sh stop"
