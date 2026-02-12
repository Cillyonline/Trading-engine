"""Public API package boundary for the HTTP layer.

Only symbols listed in ``__all__`` are part of the supported import surface.
All other modules, classes, and helpers under ``src/api`` are internal.
"""

from .main import app

__all__ = ("app",)
