"""
PyFlow.ts - Bridge Python and TypeScript with ease
"""

PYFLOWTS_VERSION = "0.2.0"
__version__ = PYFLOWTS_VERSION

from .decorators import extensity
from .cli import run

__all__ = ["extensity", "run"]
