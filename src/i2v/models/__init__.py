"""Auto-import model adapters so their @registry.register decorators fire."""
from importlib import import_module
from pkgutil import iter_modules

for _m in iter_modules(__path__):
    if not _m.name.startswith("_"):
        import_module(f"{__name__}.{_m.name}")
