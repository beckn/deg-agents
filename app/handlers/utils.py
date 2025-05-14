# app/handlers/utils.py
import importlib
from typing import Type, Any


def import_class(class_path: str) -> Type[Any]:
    """
    Dynamically imports a class given its full path.
    Example: "app.handlers.generic_handler.GenericQueryHandler"
    """
    try:
        module_path, class_name = class_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        return getattr(module, class_name)
    except (ImportError, AttributeError) as e:
        raise ImportError(f"Could not import class {class_path}: {e}")
