#!/usr/bin/env python3
"""Test new-style module that reads JSON from stdin."""

import json
import sys


def main():
    """Execute module with JSON args from stdin."""
    try:
        args = json.load(sys.stdin)
    except Exception as e:
        print(json.dumps({"failed": True, "msg": f"Failed to parse JSON: {e}"}))
        sys.exit(1)

    # Return success with args
    result = {
        "changed": args.get("change", False),
        "msg": "New-style module executed",
        "received_args": args,
    }

    print(json.dumps(result))


if __name__ == "__main__":
    main()
