#!/bin/bash
# FTL2 Multi-Host Execution Examples
# Demonstrates running FTL2 across multiple hosts in parallel

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "======================================"
echo "FTL2 Multi-Host Execution Examples"
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

# Check if containers are running
if ! docker compose ps | grep -q "Up"; then
    echo -e "${YELLOW}Warning: SSH server containers are not running${NC}"
    echo "Starting containers now..."
    echo
    ./setup.sh start
    echo
fi

echo -e "${GREEN}Using ftl2:${NC} $(which ftl2)"
echo -e "${GREEN}Target hosts:${NC} web01, web02, db01"
echo

# Example 1: Ping All Hosts (Parallel)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1. Ping all hosts (parallel execution)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Command: ftl2 -m ping -i inventory.yml"
echo
ftl2 -m ping -i inventory.yml
echo

# Example 2: Ping Only Webservers
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2. Ping webservers only"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Command: ftl2 -m ping -i inventory.yml --limit webservers"
echo
ftl2 -m ping -i inventory.yml --limit webservers
echo

# Example 3: Ping Only Databases
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3. Ping databases only"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Command: ftl2 -m ping -i inventory.yml --limit databases"
echo
ftl2 -m ping -i inventory.yml --limit databases
echo

# Example 4: Check Hostname on All Hosts
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4. Check hostname on all hosts"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Command: ftl2 -m shell -i inventory.yml -a \"cmd='hostname'\""
echo
ftl2 -m shell -i inventory.yml -a "cmd='hostname'"
echo

# Example 5: Deploy Role Markers
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "5. Deploy role markers to each group"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Setting webservers..."
ftl2 -m shell -i inventory.yml --limit webservers -a "cmd='echo \"webserver\" > /tmp/server-role'"
echo
echo "Setting databases..."
ftl2 -m shell -i inventory.yml --limit databases -a "cmd='echo \"database\" > /tmp/server-role'"
echo
echo "Verifying roles on all hosts:"
ftl2 -m shell -i inventory.yml -a "cmd='echo \"\$(hostname): \$(cat /tmp/server-role)\"'"
echo

# Example 6: Check OS Version on All Hosts
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "6. Check OS version on all hosts"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Command: ftl2 -m shell -i inventory.yml -a \"cmd='cat /etc/os-release | head -3'\""
echo
ftl2 -m shell -i inventory.yml -a "cmd='cat /etc/os-release | head -3'"
echo

# Example 7: Create Config Files
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "7. Deploy different configs to different groups"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Create web config
cat > /tmp/web.conf <<EOF
[webapp]
name=example-app
version=1.0
role=webserver
port=80
EOF

# Create db config
cat > /tmp/db.conf <<EOF
[database]
name=production-db
version=1.0
role=database
port=5432
EOF

echo "Deploying web.conf to webservers..."
ftl2 -m copy -i inventory.yml --limit webservers -a "src=/tmp/web.conf dest=/tmp/app.conf"
echo
echo "Deploying db.conf to databases..."
ftl2 -m copy -i inventory.yml --limit databases -a "src=/tmp/db.conf dest=/tmp/app.conf"
echo
echo "Verifying configs on all hosts:"
ftl2 -m shell -i inventory.yml -a "cmd='echo \"=== \$(hostname) ===\" && cat /tmp/app.conf'"
echo

# Example 8: Pattern Matching
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "8. Pattern matching - target hosts starting with 'web'"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Command: ftl2 -m shell -i inventory.yml --limit \"web*\" -a \"cmd='echo \$(hostname) matches pattern'\""
echo
ftl2 -m shell -i inventory.yml --limit "web*" -a "cmd='echo \$(hostname) matches pattern'"
echo

# Example 9: Create Directories on Specific Hosts
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "9. Create directories on all hosts"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Creating /tmp/ftl2-data on all hosts..."
ftl2 -m file -i inventory.yml -a "path=/tmp/ftl2-data state=directory mode=0755"
echo
echo "Verifying directories:"
docker compose exec -T web01 ls -lad /tmp/ftl2-data
docker compose exec -T web02 ls -lad /tmp/ftl2-data
docker compose exec -T db01 ls -lad /tmp/ftl2-data
echo

# Example 10: Gather System Info from All Hosts
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "10. Gather system information (parallel)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Command: ftl2 -m shell -i inventory.yml -a \"cmd='uname -a'\""
echo
ftl2 -m shell -i inventory.yml -a "cmd='uname -a'"
echo

# Example 11: Targeted Single Host
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "11. Target a single host (web01 only)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Command: ftl2 -m shell -i inventory.yml --limit web01 -a \"cmd='echo Only web01'\""
echo
ftl2 -m shell -i inventory.yml --limit web01 -a "cmd='echo Only web01'"
echo

# Example 12: Check Disk Space on All Hosts
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "12. Check disk space on all hosts"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Command: ftl2 -m shell -i inventory.yml -a \"cmd='df -h /tmp'\""
echo
ftl2 -m shell -i inventory.yml -a "cmd='df -h /tmp'"
echo

# Example 13: Cleanup
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "13. Cleanup test files"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Removing test files and directories from all hosts..."
ftl2 -m file -i inventory.yml -a "path=/tmp/server-role state=absent" > /dev/null 2>&1
ftl2 -m file -i inventory.yml -a "path=/tmp/app.conf state=absent" > /dev/null 2>&1
ftl2 -m file -i inventory.yml -a "path=/tmp/ftl2-data state=absent" > /dev/null 2>&1
rm -f /tmp/web.conf /tmp/db.conf
echo -e "${GREEN}Cleanup complete${NC}"
echo

echo "======================================"
echo "All multi-host examples completed!"
echo "======================================"
echo
echo -e "${BLUE}Key Observations:${NC}"
echo "  ✓ Operations ran in parallel across all hosts"
echo "  ✓ Groups allowed targeting subsets (webservers, databases)"
echo "  ✓ Pattern matching enabled flexible host selection"
echo "  ✓ Same gate zipapp reused across all hosts"
echo "  ✓ Results collected and displayed for each host"
echo
echo -e "${BLUE}Performance Notes:${NC}"
echo "  - Total execution time ≈ slowest host (not sum of all)"
echo "  - FTL2 maintains connection pool for efficiency"
echo "  - Gates cached in /tmp on each host for reuse"
echo
echo -e "${GREEN}Next Steps:${NC}"
echo "  - Review output to understand parallel execution"
echo "  - Try adding more hosts to docker-compose.yml"
echo "  - Experiment with different module combinations"
echo "  - Check gate cache: ls -la /tmp/ftl_gate_*.pyz"
echo
echo -e "${YELLOW}Stop containers:${NC}"
echo "  ./setup.sh stop"
