"""Pure calculations: no broker access, model calls, or order execution."""
from .engine import ENGINE_VERSION, evaluate, load_rules, scan

__version__ = ENGINE_VERSION
__all__ = ["evaluate", "load_rules", "scan", "ENGINE_VERSION"]
