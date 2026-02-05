"""Exception classes for FTL2 automation framework."""


class FTL2Error(Exception):
    """Base exception for all FTL2 errors."""

    pass


class ModuleNotFound(FTL2Error):
    """Raised when a module cannot be found in any module directory."""

    pass


class ModuleExecutionError(FTL2Error):
    """Raised when module execution fails."""

    pass


class GateError(FTL2Error):
    """Raised when gate operations fail."""

    pass


class InventoryError(FTL2Error):
    """Raised when inventory operations fail."""

    pass
