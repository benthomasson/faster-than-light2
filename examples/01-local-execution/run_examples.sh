#!/bin/bash
# FTL2 Local Execution Examples
# This script demonstrates various FTL2 modules running locally

set -e

echo "======================================"
echo "FTL2 Local Execution Examples"
echo "======================================"
echo

# Check if ftl2 is available
if ! command -v ftl2 &> /dev/null; then
    echo "Error: ftl2 not found in PATH"
    echo "Please install ftl2 or activate your virtual environment"
    echo
    echo "From the project root:"
    echo "  source .venv/bin/activate"
    echo "  pip install -e ."
    exit 1
fi

echo "Using ftl2: $(which ftl2)"
echo

# Example 1: Ping Module
echo "1. Testing connectivity with ping module..."
echo "   Command: ftl2 -m ping -i inventory.yml"
echo
ftl2 -m ping -i inventory.yml
echo

# Example 2: Setup Module (limited output)
echo "2. Gathering system facts with setup module..."
echo "   Command: ftl2 -m setup -i inventory.yml"
echo
ftl2 -m setup -i inventory.yml | head -20
echo "   (output truncated - full facts available)"
echo

# Example 3: File Module - Create
echo "3. Creating a test file..."
echo "   Command: ftl2 -m file -i inventory.yml -a \"path=/tmp/ftl2-test.txt state=touch\""
echo
ftl2 -m file -i inventory.yml -a "path=/tmp/ftl2-test.txt state=touch"
echo
ls -la /tmp/ftl2-test.txt
echo

# Example 4: Shell Module
echo "4. Running a shell command..."
echo "   Command: ftl2 -m shell -i inventory.yml -a \"cmd='echo Hello from FTL2'\""
echo
ftl2 -m shell -i inventory.yml -a "cmd='echo Hello from FTL2'"
echo

# Example 5: Copy Module
echo "5. Copying a file..."
echo "   Creating source file..."
echo "FTL2 Example Content" > /tmp/ftl2-source.txt
echo "   Command: ftl2 -m copy -i inventory.yml -a \"src=/tmp/ftl2-source.txt dest=/tmp/ftl2-dest.txt\""
echo
ftl2 -m copy -i inventory.yml -a "src=/tmp/ftl2-source.txt dest=/tmp/ftl2-dest.txt"
echo
echo "   Verifying copied file:"
cat /tmp/ftl2-dest.txt
echo

# Example 6: File Module - Delete
echo "6. Cleaning up test files..."
echo "   Command: ftl2 -m file -i inventory.yml -a \"path=/tmp/ftl2-test.txt state=absent\""
echo
ftl2 -m file -i inventory.yml -a "path=/tmp/ftl2-test.txt state=absent"
ftl2 -m file -i inventory.yml -a "path=/tmp/ftl2-source.txt state=absent"
ftl2 -m file -i inventory.yml -a "path=/tmp/ftl2-dest.txt state=absent"
echo

echo "======================================"
echo "All examples completed successfully!"
echo "======================================"
echo
echo "Next steps:"
echo "  - Review the output above to understand each module"
echo "  - Check the README.md for detailed explanations"
echo "  - Try example 02-remote-ssh for remote execution"
