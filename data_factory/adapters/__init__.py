"""Platform adapters. Auto-imports all adapter modules to trigger registration."""

from pathlib import Path
import importlib

_pkg_dir = Path(__file__).parent
for _f in _pkg_dir.glob("*.py"):
    if _f.name.startswith("_"):
        continue
    if _f.stem == "base":
        continue
    importlib.import_module(f"{__package__}.{_f.stem}")
