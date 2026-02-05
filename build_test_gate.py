#!/usr/bin/env python3
"""Build a test gate for manual debugging.

This script builds a gate zipapp that can be tested manually to debug
the ftl2.message import issue.

Usage:
    python build_test_gate.py

    # Then test the gate:
    python /tmp/test_gate.pyz

    # Or extract and inspect:
    cd /tmp && python -m zipfile -e test_gate.pyz gate_extracted/
    ls -la gate_extracted/
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ftl2.gate import GateBuildConfig, GateBuilder

def main():
    # Build configuration
    test_modules_dir = Path(__file__).parent / "tests" / "test_modules"

    config = GateBuildConfig(
        modules=["test_new_style"],
        module_dirs=[test_modules_dir],
        dependencies=[],
        interpreter="/usr/bin/python3",
    )

    # Build gate
    builder = GateBuilder(cache_dir=Path("/tmp"))
    gate_path, gate_hash = builder.build(config)

    print(f"✓ Built test gate: {gate_path}")
    print(f"  Hash: {gate_hash}")
    print()
    print("Test the gate:")
    print(f"  python3 {gate_path}")
    print()
    print("Extract and inspect:")
    print(f"  cd /tmp && rm -rf gate_extracted")
    print(f"  python3 -m zipfile -e {gate_path} gate_extracted/")
    print(f"  ls -la gate_extracted/")
    print(f"  cat gate_extracted/__main__.py | head -50")
    print()
    print("Debug imports:")
    print(f"  python3 -c 'import sys; sys.path.insert(0, \"{gate_path}\"); from ftl2.message import GateProtocol; print(\"SUCCESS\")'")

if __name__ == "__main__":
    main()
