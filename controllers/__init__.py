from pathlib import Path
import os
import sys
from importlib import util

IGNORE = {"__init__.py", ".DS_Store", "__pycache__"}
PACKAGE_DIR = str(Path(__file__).resolve().parent)


def _load_modules(root_directory):
    for entry in os.listdir(root_directory):
        if entry in IGNORE:
            continue

        path = os.path.join(root_directory, entry)
        if os.path.isdir(path):
            _load_modules(path)
            continue

        if not entry.endswith(".py"):
            continue

        spec = util.spec_from_file_location(f"controllers.{entry}", path)
        module = util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        globals().update({key: value for key, value in module.__dict__.items() if not key.startswith("_")})


_load_modules(PACKAGE_DIR)
