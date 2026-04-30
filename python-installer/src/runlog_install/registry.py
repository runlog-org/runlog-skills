"""Thin getter that resolves a --target name to its Host adapter class."""

from __future__ import annotations

from runlog_install import hosts as _hosts_module


def get_host(name: str) -> type:
    """Return the Host adapter class for *name*.

    Raises
    ------
    KeyError
        If *name* is not registered in ``hosts.HOSTS``.  The error message
        includes the available keys so callers can surface it directly to the
        user.
    """
    registry: dict[str, type] = getattr(_hosts_module, "HOSTS", {})
    if name not in registry:
        available = ", ".join(sorted(registry)) or "<none registered yet>"
        raise KeyError(
            f"Unknown target {name!r}. Available targets: {available}"
        )
    return registry[name]
