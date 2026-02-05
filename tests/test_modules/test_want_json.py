#!/usr/bin/env python3
"""Test module that uses WANT_JSON interface."""

import json
import sys

WANT_JSON = True


def main():
    """Execute module with JSON args from file."""
    if len(sys.argv) < 2:
        print(json.dumps({"failed": True, "msg": "No args file provided"}))
        sys.exit(1)

    args_file = sys.argv[1]

    try:
        with open(args_file) as f:
            args = json.load(f)
    except Exception as e:
        print(json.dumps({"failed": True, "msg": f"Failed to load args: {e}"}))
        sys.exit(1)

    # Return success with args
    result = {
        "changed": args.get("change", False),
        "msg": "WANT_JSON module executed",
        "received_args": args,
    }

    print(json.dumps(result))


if __name__ == "__main__":
    main()
