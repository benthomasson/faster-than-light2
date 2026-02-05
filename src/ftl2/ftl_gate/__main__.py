#!/usr/bin/env python3
"""FTL2 Gate runtime entry point for remote execution.

This module serves as the entry point when a gate executable is run
on a remote host. It establishes communication with the main process
via stdin/stdout using the length-prefixed JSON protocol and coordinates
module execution.

Message Protocol:
- 8-byte hex length prefix + JSON body
- Message format: [message_type, message_data]
- Types: Hello, Module, Shutdown, etc.

Module Execution:
Supports multiple module types:
- Binary modules: Executable files
- WANT_JSON modules: Python with JSON file args
- New-style modules: Python with JSON stdin

This is a simplified implementation focused on core functionality.
Full module type support will be added incrementally.
"""

import asyncio
import logging
import sys
import traceback
from typing import Any

# Import the gate protocol from parent package
# This will work when the gate is packaged as a .pyz
try:
    from ftl2.message import GateProtocol
except ImportError:
    # Fallback for development/testing
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from ftl2.message import GateProtocol

logger = logging.getLogger("ftl_gate")


class ModuleNotFoundError(Exception):
    """Raised when a requested module cannot be found in the gate bundle."""

    pass


class StdinReader:
    """Fallback async reader for stdin when StreamReader fails.

    Provides compatibility when asyncio's standard pipe connection
    doesn't work in certain environments.
    """

    async def read(self, n: int) -> bytes:
        """Read up to n bytes from stdin asynchronously.

        Args:
            n: Maximum number of bytes to read

        Returns:
            Bytes read from stdin
        """
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, sys.stdin.buffer.read, n)
        return result


class StdoutWriter:
    """Fallback async writer for stdout when StreamWriter fails.

    Provides compatibility when asyncio's standard pipe connection
    doesn't work in certain environments.
    """

    def write(self, data: bytes) -> None:
        """Write bytes to stdout.

        Args:
            data: Bytes to write
        """
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.flush()

    async def drain(self) -> None:
        """Drain output buffer (no-op for direct stdout writes)."""
        pass


async def connect_stdin_stdout() -> tuple[Any, Any]:
    """Establish async I/O connections to stdin and stdout.

    Attempts to use asyncio's native StreamReader/StreamWriter,
    falling back to custom implementations if needed.

    Returns:
        Tuple of (reader, writer) for protocol communication
    """
    loop = asyncio.get_event_loop()

    try:
        # Try native asyncio pipes
        stream_reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(stream_reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)

        w_transport, w_protocol = await loop.connect_write_pipe(
            asyncio.streams.FlowControlMixin,
            sys.stdout,  # type: ignore
        )
        stream_writer = asyncio.StreamWriter(
            w_transport,
            w_protocol,
            stream_reader,
            loop,  # type: ignore
        )

        reader = stream_reader
        writer = stream_writer
        logger.debug("Using native asyncio StreamReader/StreamWriter")

    except ValueError as e:
        # Fall back to custom reader/writer
        logger.debug(f"Falling back to custom reader/writer: {e}")
        reader = StdinReader()
        writer = StdoutWriter()

    return reader, writer


async def execute_module_stub(module_name: str, module: str | None, module_args: dict) -> dict:
    """Execute a module (stub implementation).

    This is a placeholder that will be replaced with full module
    execution logic.

    Args:
        module_name: Name of the module to execute
        module: Optional module content (base64 encoded)
        module_args: Arguments to pass to the module

    Returns:
        Module result dictionary
    """
    logger.info(f"Executing module: {module_name} with args: {module_args}")

    # For now, just return a success result
    # TODO: Implement actual module execution
    return {
        "stdout": f"Module {module_name} executed (stub)",
        "stderr": "",
        "rc": 0,
        "changed": False,
    }


async def main(args: list[str]) -> int | None:
    """Main entry point for the FTL2 gate process.

    Initializes logging, establishes communication, and enters the
    message processing loop.

    Args:
        args: Command-line arguments (currently unused)

    Returns:
        Exit code: None for normal shutdown, 1 for error
    """
    # Set up logging
    logging.basicConfig(
        format="%(asctime)s - %(message)s",
        filename="/tmp/ftl2_gate.log",
        level=logging.DEBUG,
    )

    logger.info("=" * 60)
    logger.info("FTL2 Gate starting")
    logger.info(f"Python: {sys.executable}")
    logger.info(f"Version: {sys.version}")
    logger.info(f"Path: {sys.path[:3]}...")  # First 3 entries
    logger.info("=" * 60)

    # Connect to stdin/stdout
    try:
        reader, writer = await connect_stdin_stdout()
        logger.info("Connected to stdin/stdout")
    except Exception as e:
        logger.error(f"Failed to connect stdin/stdout: {e}")
        return 1

    # Initialize protocol
    protocol = GateProtocol()

    # Message processing loop
    while True:
        try:
            # Read message
            msg = await protocol.read_message(reader)

            if msg is None:
                # EOF - normal shutdown
                logger.info("EOF received, shutting down")
                try:
                    await protocol.send_message(writer, "Goodbye", {})
                except Exception:
                    pass  # Ignore errors during shutdown
                return None

            msg_type, data = msg
            logger.debug(f"Received message: {msg_type}")

            # Handle message by type
            if msg_type == "Hello":
                # Echo hello message
                logger.info("Hello received")
                await protocol.send_message(writer, "Hello", data)

            elif msg_type == "Module":
                # Execute module
                logger.info(f"Module execution requested: {data}")

                if not isinstance(data, dict):
                    await protocol.send_message(writer, "Error", {"message": "Invalid Module data"})
                    continue

                try:
                    result = await execute_module_stub(
                        data.get("module_name", ""),
                        data.get("module"),
                        data.get("module_args", {}),
                    )
                    await protocol.send_message(writer, "ModuleResult", result)

                except ModuleNotFoundError as e:
                    await protocol.send_message(
                        writer,
                        "ModuleNotFound",
                        {"message": f"Module not found: {e}"},
                    )

                except Exception as e:
                    logger.exception("Module execution failed")
                    await protocol.send_message(
                        writer,
                        "Error",
                        {
                            "message": f"Module execution failed: {e}",
                            "traceback": traceback.format_exc(),
                        },
                    )

            elif msg_type == "Shutdown":
                # Clean shutdown
                logger.info("Shutdown requested")
                await protocol.send_message(writer, "Goodbye", {})
                return None

            else:
                # Unknown message type
                logger.warning(f"Unknown message type: {msg_type}")
                await protocol.send_message(
                    writer, "Error", {"message": f"Unknown message type: {msg_type}"}
                )

        except ModuleNotFoundError as e:
            # Module not in bundle
            logger.warning(f"Module not found: {e}")
            try:
                await protocol.send_message(writer, "ModuleNotFound", {"message": str(e)})
            except Exception:
                pass  # Continue even if we can't send response

        except Exception as e:
            # Unexpected error - send error message and exit
            logger.error(f"Gate system error: {e}")
            logger.error(traceback.format_exc())

            try:
                await protocol.send_message(
                    writer,
                    "GateSystemError",
                    {
                        "message": f"System error: {e}",
                        "traceback": traceback.format_exc(),
                    },
                )
            except Exception:
                pass  # Can't send response

            return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main(sys.argv[1:]))
        sys.exit(exit_code or 0)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(130)  # Standard SIGINT exit code
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)
