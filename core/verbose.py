"""Verbose output for pipeline observability.

Module-level singleton. Call configure() once at boot,
then use vprint/header/stage/step/detail from anywhere.

Levels:
    0 (OFF)   — silent (default)
    1 (INFO)  — header, stage, stage_end
    2 (DEBUG) — + step, vprint
    3 (TRACE) — + detail
"""

from __future__ import annotations

from enum import IntEnum

_level: int = 0


class Level(IntEnum):
    """Verbosity levels."""

    OFF = 0
    INFO = 1
    DEBUG = 2
    TRACE = 3


def configure(level: int) -> None:
    """Set verbosity level. Called once at boot."""
    global _level
    _level = level


def get_level() -> int:
    """Return current verbosity level."""
    return _level


def is_verbose() -> bool:
    """Check if verbose mode is on (any level > 0)."""
    return _level > 0


def vprint(msg: str) -> None:
    """Print only at DEBUG (2) or higher."""
    if _level >= Level.DEBUG:
        print(msg)


def header(text: str) -> None:
    """Bold run-level header. Prints at INFO (1) or higher."""
    if _level >= Level.INFO:
        print(f"\n═══ {text} ═══\n")


def stage(name: str, description: str) -> None:
    """Stage header with brief explanation. Prints at INFO (1) or higher."""
    if _level >= Level.INFO:
        print(f"── {name}: {description} ──")


def stage_end(name: str, items_out: int, errors: int, duration: float) -> None:
    """Stage completion line. Prints at INFO (1) or higher."""
    if _level >= Level.INFO:
        print(
            f"── {name} done ({items_out} out, {errors} errors, {duration:.2f}s) ──\n"
        )


def step(text: str) -> None:
    """Indented sub-header within a stage. Prints at DEBUG (2) or higher."""
    if _level >= Level.DEBUG:
        print(f"  {text}")


def detail(text: str) -> None:
    """Further indented detail line. Prints at TRACE (3) only."""
    if _level >= Level.TRACE:
        print(f"    {text}")
