#!/usr/bin/env python3
"""Interactive debugger for FTL2 gate processes.

Launches a gate .pyz and provides an interactive prompt for sending
messages using the length-prefixed JSON protocol.

Usage:
    python tools/gate_debug.py <gate.pyz>
    python tools/gate_debug.py ~/.ftl/ftl_gate_*.pyz

Built-in commands:
    hello       Send a Hello message
    shutdown    Send a Shutdown message and exit
    module      Send a Module execution request
    raw         Send a raw JSON message
    quit        Close stdin and exit

Examples:
    $ python tools/gate_debug.py ~/.ftl/ftl_gate_abc123.pyz
    gate> hello
    << Hello: {}
    gate> module ping
    << ModuleResult: {"stdout": "...", "stderr": ""}
    gate> shutdown
    << Goodbye: {}
"""

import json
import subprocess
import sys
import threading


def encode_message(msg_type: str, data: dict) -> bytes:
    """Encode a message using the gate protocol (8-byte hex length + JSON)."""
    body = json.dumps([msg_type, data])
    length = len(body.encode("utf-8"))
    return f"{length:08x}{body}".encode("utf-8")


def decode_messages(raw: bytes) -> list[tuple[str, dict]]:
    """Decode one or more length-prefixed messages from raw bytes."""
    messages = []
    pos = 0
    while pos < len(raw):
        if pos + 8 > len(raw):
            break
        length = int(raw[pos : pos + 8].decode("ascii"), 16)
        pos += 8
        body = raw[pos : pos + length].decode("utf-8")
        pos += length
        msg_type, data = json.loads(body)
        messages.append((msg_type, data))
    return messages


def reader_thread(proc: subprocess.Popen) -> None:
    """Read and display gate responses in a background thread."""
    buf = b""
    while True:
        chunk = proc.stdout.read(1)
        if not chunk:
            break
        buf += chunk
        # Try to parse complete messages from buffer
        while len(buf) >= 8:
            try:
                length = int(buf[:8].decode("ascii"), 16)
            except ValueError:
                break
            if len(buf) < 8 + length:
                break
            body = buf[8 : 8 + length].decode("utf-8")
            buf = buf[8 + length :]
            msg_type, data = json.loads(body)
            if msg_type == "InfoResult":
                print(f"\n<< {msg_type}:")
                for key, val in data.items():
                    print(f"   {key:20s} {val}")
            elif msg_type == "ListModulesResult":
                modules = data.get("modules", [])
                print(f"\n<< {msg_type}: {len(modules)} module(s)")
                for m in modules:
                    print(f"   {m['name']:30s} {m['type']}")
            else:
                print(f"\n<< {msg_type}: {json.dumps(data)}")
            print("gate> ", end="", flush=True)


def main() -> None:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <gate.pyz>")
        sys.exit(1)

    gate_path = sys.argv[1]
    print(f"Launching gate: {gate_path}")
    print("Commands: hello, info, list, shutdown, module <name> [args_json], raw <json>, quit")
    print()

    proc = subprocess.Popen(
        [sys.executable, gate_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )

    # Start background reader
    t = threading.Thread(target=reader_thread, args=(proc,), daemon=True)
    t.start()

    try:
        while True:
            try:
                line = input("gate> ").strip()
            except EOFError:
                break

            if not line:
                continue

            parts = line.split(None, 1)
            cmd = parts[0].lower()

            if cmd == "hello":
                msg = encode_message("Hello", {})
                proc.stdin.write(msg)
                proc.stdin.flush()

            elif cmd == "info":
                msg = encode_message("Info", {})
                proc.stdin.write(msg)
                proc.stdin.flush()

            elif cmd == "list":
                msg = encode_message("ListModules", {})
                proc.stdin.write(msg)
                proc.stdin.flush()

            elif cmd == "shutdown":
                msg = encode_message("Shutdown", {})
                proc.stdin.write(msg)
                proc.stdin.flush()
                proc.stdin.close()
                proc.wait()
                break

            elif cmd == "module":
                args = parts[1] if len(parts) > 1 else ""
                module_parts = args.split(None, 1)
                module_name = module_parts[0] if module_parts else "ping"
                module_args = {}
                if len(module_parts) > 1:
                    try:
                        module_args = json.loads(module_parts[1])
                    except json.JSONDecodeError:
                        print("Invalid JSON for module args")
                        continue
                msg = encode_message(
                    "Module",
                    {"module_name": module_name, "module_args": module_args},
                )
                proc.stdin.write(msg)
                proc.stdin.flush()

            elif cmd == "raw":
                if len(parts) < 2:
                    print("Usage: raw <json>")
                    continue
                try:
                    parsed = json.loads(parts[1])
                    if isinstance(parsed, list) and len(parsed) == 2:
                        msg = encode_message(parsed[0], parsed[1])
                    else:
                        print("Expected [msg_type, data]")
                        continue
                except json.JSONDecodeError:
                    print("Invalid JSON")
                    continue
                proc.stdin.write(msg)
                proc.stdin.flush()

            elif cmd == "quit":
                proc.stdin.close()
                proc.wait()
                break

            else:
                print(f"Unknown command: {cmd}")
                print("Commands: hello, info, list, shutdown, module <name> [args_json], raw <json>, quit")

    except KeyboardInterrupt:
        print()
    finally:
        if proc.poll() is None:
            proc.stdin.close()
            proc.wait()
        # Give reader thread a moment to print final messages
        t.join(timeout=0.5)


if __name__ == "__main__":
    main()
