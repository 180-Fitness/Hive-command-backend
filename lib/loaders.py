from importlib import import_module
from inspect import isclass
from os import walk
from os.path import abspath, dirname, join
import sys

from flask_sqlalchemy import Model

__all__ = ("get_models", "load_models")

PROJECT_ROOT = abspath(join(dirname(abspath(__file__)), ".."))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def iter_model_modules(package="models"):
    base_dir = abspath(join(PROJECT_ROOT, package))

    for root, _dirs, files in walk(base_dir):
        relative_root = root[len(PROJECT_ROOT) :].lstrip("/").replace("/", ".")

        for filename in files:
            if filename.endswith(".py") and not filename.startswith("__init__"):
                yield ".".join([relative_root, filename[:-3]])


def dynamic_loader(package, predicate):
    discovered = []

    for module_path in iter_model_modules(package):
        module = import_module(module_path)
        candidates = []

        if hasattr(module, "__all__"):
            candidates.extend(getattr(module, name) for name in module.__all__)
        else:
            candidates.extend(
                value for value in module.__dict__.values() if predicate(value)
            )

        discovered.extend([item for item in candidates if predicate(item) and item not in discovered])

    return discovered


def is_model(item):
    return isclass(item) and issubclass(item, Model) and hasattr(item, "__tablename__")


def get_models():
    return dynamic_loader("models", is_model)


def load_models():
    from sys import modules

    for model in dynamic_loader("models", is_model):
        setattr(modules[__name__], model.__name__, model)
