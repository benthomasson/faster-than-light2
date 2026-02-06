"""Progress reporting for FTL2.

Provides callback-based progress tracking for module execution,
supporting both text and JSON output formats.
"""

import json
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Protocol


@dataclass
class ProgressEvent:
    """A progress event during execution.

    Attributes:
        event_type: Type of event (started, completed, failed, retrying)
        host: Host name
        timestamp: When the event occurred
        details: Additional event-specific details
    """

    event_type: str
    host: str
    timestamp: str
    details: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "event": self.event_type,
            "host": self.host,
            "timestamp": self.timestamp,
        }
        result.update(self.details)
        return result

    def to_json(self) -> str:
        """Convert to JSON string (NDJSON format)."""
        return json.dumps(self.to_dict())


class ProgressCallback(Protocol):
    """Protocol for progress callbacks."""

    def __call__(self, event: ProgressEvent) -> None:
        """Handle a progress event."""
        ...


class ProgressReporter(ABC):
    """Base class for progress reporters."""

    @abstractmethod
    def on_execution_start(self, total_hosts: int, module: str) -> None:
        """Called when execution starts."""
        pass

    @abstractmethod
    def on_host_start(self, host: str) -> None:
        """Called when a host execution starts."""
        pass

    @abstractmethod
    def on_host_complete(
        self,
        host: str,
        success: bool,
        changed: bool,
        duration: float,
        error: str | None = None,
    ) -> None:
        """Called when a host execution completes."""
        pass

    @abstractmethod
    def on_host_retry(
        self,
        host: str,
        attempt: int,
        max_attempts: int,
        error: str,
        delay: float,
    ) -> None:
        """Called when a host is about to be retried."""
        pass

    @abstractmethod
    def on_execution_complete(
        self,
        total: int,
        successful: int,
        failed: int,
        duration: float,
    ) -> None:
        """Called when execution completes."""
        pass


class JsonProgressReporter(ProgressReporter):
    """Reports progress as NDJSON (newline-delimited JSON) events."""

    def __init__(self, output: Any = None) -> None:
        """Initialize JSON progress reporter.

        Args:
            output: Output stream (defaults to sys.stderr to not pollute stdout)
        """
        self.output = output or sys.stderr

    def _emit(self, event: ProgressEvent) -> None:
        """Emit a progress event."""
        print(event.to_json(), file=self.output, flush=True)

    def _now(self) -> str:
        """Get current timestamp."""
        return datetime.now(timezone.utc).isoformat()

    def on_execution_start(self, total_hosts: int, module: str) -> None:
        """Called when execution starts."""
        self._emit(ProgressEvent(
            event_type="execution_start",
            host="*",
            timestamp=self._now(),
            details={"total_hosts": total_hosts, "module": module},
        ))

    def on_host_start(self, host: str) -> None:
        """Called when a host execution starts."""
        self._emit(ProgressEvent(
            event_type="host_start",
            host=host,
            timestamp=self._now(),
            details={},
        ))

    def on_host_complete(
        self,
        host: str,
        success: bool,
        changed: bool,
        duration: float,
        error: str | None = None,
    ) -> None:
        """Called when a host execution completes."""
        details: dict[str, Any] = {
            "success": success,
            "changed": changed,
            "duration": round(duration, 3),
        }
        if error:
            details["error"] = error

        self._emit(ProgressEvent(
            event_type="host_complete",
            host=host,
            timestamp=self._now(),
            details=details,
        ))

    def on_host_retry(
        self,
        host: str,
        attempt: int,
        max_attempts: int,
        error: str,
        delay: float,
    ) -> None:
        """Called when a host is about to be retried."""
        self._emit(ProgressEvent(
            event_type="host_retry",
            host=host,
            timestamp=self._now(),
            details={
                "attempt": attempt,
                "max_attempts": max_attempts,
                "error": error,
                "delay": round(delay, 1),
            },
        ))

    def on_execution_complete(
        self,
        total: int,
        successful: int,
        failed: int,
        duration: float,
    ) -> None:
        """Called when execution completes."""
        self._emit(ProgressEvent(
            event_type="execution_complete",
            host="*",
            timestamp=self._now(),
            details={
                "total": total,
                "successful": successful,
                "failed": failed,
                "duration": round(duration, 3),
            },
        ))


class TextProgressReporter(ProgressReporter):
    """Reports progress as human-readable text."""

    def __init__(self, output: Any = None) -> None:
        """Initialize text progress reporter.

        Args:
            output: Output stream (defaults to sys.stderr)
        """
        self.output = output or sys.stderr
        self.completed = 0
        self.total = 0

    def _emit(self, message: str) -> None:
        """Emit a progress message."""
        print(message, file=self.output, flush=True)

    def on_execution_start(self, total_hosts: int, module: str) -> None:
        """Called when execution starts."""
        self.total = total_hosts
        self.completed = 0
        self._emit(f"Executing module '{module}' on {total_hosts} host(s)...")

    def on_host_start(self, host: str) -> None:
        """Called when a host execution starts."""
        # Don't emit for start in text mode to reduce noise
        pass

    def on_host_complete(
        self,
        host: str,
        success: bool,
        changed: bool,
        duration: float,
        error: str | None = None,
    ) -> None:
        """Called when a host execution completes."""
        self.completed += 1
        status = "✓" if success else "✗"
        changed_str = " (changed)" if changed else ""

        if success:
            self._emit(f"  [{self.completed}/{self.total}] {status} {host}{changed_str} ({duration:.2f}s)")
        else:
            error_msg = f": {error}" if error else ""
            self._emit(f"  [{self.completed}/{self.total}] {status} {host} FAILED{error_msg}")

    def on_host_retry(
        self,
        host: str,
        attempt: int,
        max_attempts: int,
        error: str,
        delay: float,
    ) -> None:
        """Called when a host is about to be retried."""
        self._emit(f"  ⟳ {host}: retrying in {delay:.0f}s (attempt {attempt}/{max_attempts}): {error}")

    def on_execution_complete(
        self,
        total: int,
        successful: int,
        failed: int,
        duration: float,
    ) -> None:
        """Called when execution completes."""
        if failed == 0:
            self._emit(f"Completed: {successful}/{total} succeeded in {duration:.2f}s")
        else:
            self._emit(f"Completed: {successful}/{total} succeeded, {failed} failed in {duration:.2f}s")


class NullProgressReporter(ProgressReporter):
    """No-op progress reporter that discards all events."""

    def on_execution_start(self, total_hosts: int, module: str) -> None:
        pass

    def on_host_start(self, host: str) -> None:
        pass

    def on_host_complete(
        self,
        host: str,
        success: bool,
        changed: bool,
        duration: float,
        error: str | None = None,
    ) -> None:
        pass

    def on_host_retry(
        self,
        host: str,
        attempt: int,
        max_attempts: int,
        error: str,
        delay: float,
    ) -> None:
        pass

    def on_execution_complete(
        self,
        total: int,
        successful: int,
        failed: int,
        duration: float,
    ) -> None:
        pass


def create_progress_reporter(
    enabled: bool,
    json_format: bool = False,
    output: Any = None,
) -> ProgressReporter:
    """Create a progress reporter.

    Args:
        enabled: Whether progress reporting is enabled
        json_format: Use JSON format instead of text
        output: Output stream (defaults to sys.stderr)

    Returns:
        ProgressReporter instance
    """
    if not enabled:
        return NullProgressReporter()

    if json_format:
        return JsonProgressReporter(output)
    else:
        return TextProgressReporter(output)
