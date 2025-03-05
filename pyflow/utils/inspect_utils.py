"""
Utilities for inspecting Python objects.
"""
import inspect
import importlib
import pkgutil
from typing import Any, Dict, List, Callable, Type, get_type_hints, Set

def get_module_classes(module_name: str) -> Dict[str, Type]:
    """Get all classes defined in a module."""
    module = importlib.import_module(module_name)
    return {
        name: obj for name, obj in inspect.getmembers(module, inspect.isclass)
        if obj.__module__ == module_name
    }

def get_module_functions(module_name: str) -> Dict[str, Callable]:
    """Get all functions defined in a module."""
    module = importlib.import_module(module_name)
    return {
        name: obj for name, obj in inspect.getmembers(module, inspect.isfunction)
        if obj.__module__ == module_name
    }

def get_all_submodules(package_name: str) -> List[str]:
    """Get all submodules of a package recursively."""
    package = importlib.import_module(package_name)
    results = []

    if hasattr(package, '__path__'):
        for _, name, is_pkg in pkgutil.walk_packages(package.__path__, package.__name__ + '.'):
            results.append(name)

    return results

def get_function_details(func: Callable) -> Dict[str, Any]:
    """Get detailed information about a function."""
    signature = inspect.signature(func)
    type_hints = get_type_hints(func)

    params = []
    for name, param in signature.parameters.items():
        param_type = type_hints.get(name, Any)
        default = param.default if param.default is not inspect.Parameter.empty else None
        params.append({
            'name': name,
            'type': param_type,
            'default': default,
            'has_default': param.default is not inspect.Parameter.empty
        })

    return {
        'name': func.__name__,
        'qualname': func.__qualname__,
        'module': func.__module__,
        'params': params,
        'return_type': type_hints.get('return', Any),
        'doc': inspect.getdoc(func) or ""
    }

def get_class_details(cls: Type) -> Dict[str, Any]:
    """Get detailed information about a class."""
    methods = {}
    for name, method in inspect.getmembers(cls, inspect.isfunction):
        if not name.startswith('_') or name == '__init__':
            methods[name] = get_function_details(method)

    attributes = {}
    for name, value in cls.__dict__.items():
        if not name.startswith('_') and not callable(value):
            attributes[name] = {
                'name': name,
                'type': type(value),
                'value': value
            }

    # Add type-annotated attributes
    for name, type_hint in getattr(cls, '__annotations__', {}).items():
        if name in attributes:
            attributes[name]['type_hint'] = type_hint
        else:
            attributes[name] = {
                'name': name,
                'type_hint': type_hint,
                'value': getattr(cls, name, None)
            }

    return {
        'name': cls.__name__,
        'qualname': cls.__qualname__,
        'module': cls.__module__,
        'methods': methods,
        'attributes': attributes,
        'doc': inspect.getdoc(cls) or ""
    }

def get_referenced_types(func_or_class: Any) -> Set[Type]:
    """Extract all referenced types from a function signature or class."""
    referenced_types = set()

    if inspect.isfunction(func_or_class):
        type_hints = get_type_hints(func_or_class)

        # Add parameter types
        for param_type in type_hints.values():
            if inspect.isclass(param_type) and not any(param_type is builtin for builtin in [str, int, float, bool, list, dict, set, tuple]):
                referenced_types.add(param_type)

    elif inspect.isclass(func_or_class):
        # Check all method signatures
        for _, method in inspect.getmembers(func_or_class, inspect.isfunction):
            referenced_types.update(get_referenced_types(method))

        # Check class annotations
        for _, type_hint in getattr(func_or_class, '__annotations__', {}).items():
            if inspect.isclass(type_hint) and not any(type_hint is builtin for builtin in [str, int, float, bool, list, dict, set, tuple]):
                referenced_types.add(type_hint)

    return referenced_types

def get_all_referenced_types(module_name: str) -> Dict[str, Type]:
    """Get all types referenced in a module's PyFlow.ts-decorated elements."""
    module = importlib.import_module(module_name)
    referenced_types = {}

    for name, obj in inspect.getmembers(module):
        if inspect.isclass(obj) and obj.__module__ == module_name:
            referenced_types[obj.__name__] = obj

            # Also get types referenced by this class
            for ref_type in get_referenced_types(obj):
                if ref_type.__module__ == module_name:
                    referenced_types[ref_type.__name__] = ref_type

    return referenced_types