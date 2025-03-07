"""
Utilities for inspecting Python objects.
"""
import inspect
import importlib
import os
import pkgutil
import re
import logging
logging.basicConfig(level=logging.INFO)
from typing import Any, Dict, List, Callable, Type, get_type_hints, Set, Tuple
import sys

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

    # Handle functions
    if inspect.isfunction(func_or_class):
        try:
            type_hints = get_type_hints(func_or_class)

            # Add parameter types and return type
            for param_type in type_hints.values():
                _extract_types_recursively(param_type, referenced_types)

        except (TypeError, NameError, ValueError):
            # Handle forward references and other typing errors
            pass

    # Handle classes
    elif inspect.isclass(func_or_class):
        # Process base classes
        for base in func_or_class.__bases__:
            if base is not object and not base.__module__.startswith('typing'):
                referenced_types.add(base)
                referenced_types.update(get_referenced_types(base))

        # Check all method signatures
        for _, method in inspect.getmembers(func_or_class, inspect.isfunction):
            try:
                method_types = get_referenced_types(method)
                referenced_types.update(method_types)
            except (TypeError, ValueError):
                pass

        # Check class annotations
        try:
            for _, type_hint in getattr(func_or_class, '__annotations__', {}).items():
                _extract_types_recursively(type_hint, referenced_types)
        except (TypeError, NameError):
            pass

        # Also check instance variables defined in __init__
        if hasattr(func_or_class, '__init__'):
            try:
                init_method = func_or_class.__init__
                init_source = inspect.getsource(init_method)

                # Look for self.attr = ... patterns
                for line in init_source.splitlines():
                    if 'self.' in line and '=' in line:
                        # This is a simple heuristic to find instance vars
                        # A more robust approach would use AST parsing
                        pass
            except (IOError, TypeError):
                pass

    return referenced_types

def _extract_types_recursively(hint_type, referenced_types: Set[Type]) -> None:
    """Extract class types from a type hint recursively."""
    # Direct class reference
    if inspect.isclass(hint_type):
        if (hint_type.__module__ != 'builtins' and
            hint_type is not type(None) and
            not hint_type.__module__.startswith('typing')):
            referenced_types.add(hint_type)

    # Generic types like List[T], Dict[K,V], etc.
    elif hasattr(hint_type, '__origin__') and hasattr(hint_type, '__args__'):
        for arg in hint_type.__args__:
            _extract_types_recursively(arg, referenced_types)

    # Union types or similar with __args__
    elif hasattr(hint_type, '__args__'):
        for arg in hint_type.__args__:
            if arg is not type(None):  # Skip None in Optional[T]
                _extract_types_recursively(arg, referenced_types)

def get_all_referenced_types(module_name: str) -> Dict[str, Type]:
    """
    Get all types referenced in function signatures and class definitions in a module.
    Also includes types referenced in decorated methods and classes.

    Args:
        module_name: The name of the module to inspect

    Returns:
        A dictionary mapping class names to class objects
    """
    try:
        module = importlib.import_module(module_name)
    except ImportError:
        print(f"Warning: Could not import module {module_name}")
        return {}

    # Store all referenced types
    referenced_types = {}

    # Track visited classes to avoid infinite recursion
    visited = set()

    # First, find all @extensity decorated classes and functions in the module
    decorated_items = []
    for name, obj in inspect.getmembers(module):
        is_decorated = getattr(obj, '_pyflow_decorated', False)
        if is_decorated:
            decorated_items.append(obj)

    # Get all classes defined in the module
    for name, obj in inspect.getmembers(module, inspect.isclass):
        if obj.__module__ == module_name:
            referenced_types[obj.__name__] = obj

            # Process inheritance tree
            _process_class_inheritance(obj, referenced_types, visited)

    # Process all decorated items to find types
    for item in decorated_items:
        if inspect.isclass(item):
            # Add all types referenced by this class
            for ref_type in get_referenced_types(item):
                referenced_types[ref_type.__name__] = ref_type
                _process_class_inheritance(ref_type, referenced_types, visited)

        elif inspect.isfunction(item):
            # Add all types referenced by this function
            try:
                hints = get_type_hints(item)
                for hint_type in hints.values():
                    _process_type_hint(hint_type, referenced_types, visited)
            except (TypeError, NameError, ValueError):
                pass

    # Process all functions to find referenced types in signatures
    for name, obj in inspect.getmembers(module, inspect.isfunction):
        if obj.__module__ == module_name:
            try:
                hints = get_type_hints(obj)
                for hint_type in hints.values():
                    _process_type_hint(hint_type, referenced_types, visited)
            except (TypeError, NameError, ValueError):
                pass

    # Look for any classes with @extensity decorated methods
    for name, obj in inspect.getmembers(module, inspect.isclass):
        if obj.__module__ == module_name:
            for method_name, method in inspect.getmembers(obj, inspect.isfunction):
                is_decorated = getattr(method, '_pyflow_decorated', False)
                if is_decorated:
                    # Add this class
                    referenced_types[obj.__name__] = obj
                    _process_class_inheritance(obj, referenced_types, visited)

                    # Add types referenced in method signature
                    try:
                        hints = get_type_hints(method)
                        for hint_type in hints.values():
                            _process_type_hint(hint_type, referenced_types, visited)
                    except (TypeError, NameError, ValueError):
                        pass
                    break  # Found at least one decorated method, no need to check others

    return referenced_types

def _process_class_inheritance(cls, referenced_types, visited):
    """Process a class and its inheritance tree, adding all to the referenced_types dict."""
    if cls in visited or cls is object:
        return

    visited.add(cls)

    # Add the class
    referenced_types[cls.__name__] = cls

    # Process base classes
    for base in cls.__bases__:
        if base is not object and not base.__module__.startswith('typing'):
            _process_class_inheritance(base, referenced_types, visited)

def _process_type_hint(hint_type, referenced_types, visited):
    """Process a type hint and add all referenced classes to referenced_types."""
    # Handle direct class references
    if inspect.isclass(hint_type):
        if (hint_type.__module__ != 'builtins' and
            hint_type is not type(None) and
            not hint_type.__module__.startswith('typing')):
            referenced_types[hint_type.__name__] = hint_type
            _process_class_inheritance(hint_type, referenced_types, visited)

    # Handle generic types (List[T], Dict[K,V], etc.)
    elif hasattr(hint_type, '__origin__') and hasattr(hint_type, '__args__'):
        for arg in hint_type.__args__:
            _process_type_hint(arg, referenced_types, visited)

    # Handle Union types or similar with __args__
    elif hasattr(hint_type, '__args__'):
        for arg in hint_type.__args__:
            if arg is not type(None):  # Skip None in Optional[T]
                _process_type_hint(arg, referenced_types, visited)

def _extract_types_from_hint(hint_type, referenced_types):
    """Extract class types from a type hint."""
    # Delegate to the more comprehensive recursive function
    _extract_types_recursively(hint_type, set(referenced_types.values()))

    # If it's a direct class reference
    if inspect.isclass(hint_type):
        if not hint_type.__module__.startswith('typing') and hint_type.__module__ != 'builtins':
            referenced_types[hint_type.__name__] = hint_type

    # If it's a generic type like List[T], Dict[K,V], etc.
    elif hasattr(hint_type, '__origin__') and hasattr(hint_type, '__args__'):
        for arg in hint_type.__args__:
            _extract_types_from_hint(arg, referenced_types)

    # If it's a Union type or similar with __args__
    elif hasattr(hint_type, '__args__'):
        for arg in hint_type.__args__:
            if arg is not type(None):  # Skip None in Optional[T]
                _extract_types_from_hint(arg, referenced_types)

def get_decorated_items_in_module(module_name: str) -> Tuple[List[Type], List[Callable]]:
    """Get all @extensity decorated classes and functions in a module."""
    try:
        # First check if this is a known web framework module that might cause issues
        is_web_framework = any(framework in module_name for framework in ["flask", "django", "fastapi", "web"])

        # Use a more careful import approach for potential web framework modules
        if is_web_framework:
            # For web modules, we need to be cautious about imports
            return _safe_get_decorated_items(module_name)

        # Standard import for regular modules
        module = importlib.import_module(module_name)
    except ImportError:
        print(f"Warning: Could not import module {module_name}")
        return [], []
    except RuntimeError as e:
        # This is likely a Flask "working outside request context" error or similar
        if "request context" in str(e).lower():
            print(f"Web framework module detected: {module_name} - using alternate import method")
            return _safe_get_decorated_items(module_name)
        raise

    decorated_classes = []
    decorated_functions = []

    try:
        # Process module members
        for name, obj in inspect.getmembers(module):
            try:
                is_decorated = getattr(obj, '_pyflow_decorated', False)
                if is_decorated:
                    if inspect.isclass(obj) and obj.__module__ == module_name:
                        decorated_classes.append(obj)
                    elif inspect.isfunction(obj) and obj.__module__ == module_name:
                        decorated_functions.append(obj)
            except (RuntimeError, AttributeError):
                # Skip objects that cause errors when accessed
                continue

        # Also look for classes with decorated methods
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if obj.__module__ == module_name and obj not in decorated_classes:
                has_decorated_method = False
                for method_name, method in inspect.getmembers(obj, inspect.isfunction):
                    try:
                        if getattr(method, '_pyflow_decorated', False):
                            decorated_classes.append(obj)
                            has_decorated_method = True
                            break
                    except (RuntimeError, AttributeError):
                        # Skip methods that cause errors when accessed
                        continue

                if has_decorated_method:
                    break

        # If we didn't find any decorated items, try source code scanning
        if not decorated_classes and not decorated_functions:
            try:
                file_path = inspect.getfile(module)
                with open(file_path, 'r') as f:
                    source = f.read()

                # Look for @extensity decorators in the source code
                decorator_pattern = r'@\s*extensity\s*\n\s*(class|def)\s+([A-Za-z0-9_]+)'
                matches = re.findall(decorator_pattern, source)

                if matches:
                    logging.debug(f"Found potential decorated items in source: {matches}")

                    # Check each potential match
                    for kind, name in matches:
                        if hasattr(module, name):
                            item = getattr(module, name)
                            # Manually mark as decorated if needed
                            if not getattr(item, '_pyflow_decorated', False):
                                setattr(item, '_pyflow_decorated', True)

                            if kind == 'class' and item not in decorated_classes:
                                decorated_classes.append(item)
                                logging.debug(f"Added class from source analysis: {name}")
                            elif kind == 'def' and item not in decorated_functions:
                                decorated_functions.append(item)
                                logging.debug(f"Added function from source analysis: {name}")
            except (TypeError, IOError):
                # Module might not have a file, or file might not be readable
                pass

    except RuntimeError as e:
        if "request context" in str(e).lower():
            # Fall back to safer inspection method
            return _safe_get_decorated_items(module_name)
        raise

    # Also check registry for any items from this module that might have been missed
    from ..core import registry

    for class_name, class_info in registry.classes.items():
        if class_info['module'] == module_name:
            cls = class_info.get('cls')
            if cls and cls not in decorated_classes:
                decorated_classes.append(cls)
                logging.debug(f"Added class from registry: {cls.__name__}")

    for func_name, func_info in registry.functions.items():
        if func_info['module'] == module_name:
            func = func_info.get('func')
            if func and func not in decorated_functions:
                decorated_functions.append(func)
                logging.debug(f"Added function from registry: {func.__name__}")

    return decorated_classes, decorated_functions

def _safe_get_decorated_items(module_name: str) -> Tuple[List[Type], List[Callable]]:
    """
    Safely get decorated items from a module that might contain web framework code.
    Uses source code inspection rather than direct import to avoid context errors.
    """
    try:
        # First try to find the module file
        try:
            module_spec = importlib.util.find_spec(module_name)
            if not module_spec or not module_spec.origin:
                logging.debug(f"Could not find module file for {module_name}")
                return [], []

            module_file = module_spec.origin
        except (ImportError, AttributeError):
            # Try alternative approach - find by converting dots to slashes
            parts = module_name.split('.')
            potential_path = os.path.join(*parts) + '.py'

            # Check various base directories
            for base_dir in sys.path:
                full_path = os.path.join(base_dir, potential_path)
                if os.path.exists(full_path):
                    module_file = full_path
                    break
            else:
                logging.debug(f"Could not find module file for {module_name}")
                return [], []

        # Read the source code to find decorated items
        with open(module_file, 'r') as f:
            source = f.read()

        # Find all class and function definitions with @extensity
        # This is a simple regex approach, not perfect but works for common cases
        decorator_pattern = r'@\s*extensity\s*\n\s*(class|def)\s+([A-Za-z0-9_]+)'
        matches = re.findall(decorator_pattern, source)

        # Extract names of decorated classes and functions
        classes = [name for kind, name in matches if kind == 'class']
        functions = [name for kind, name in matches if kind == 'def']

        print(f"Found {len(classes)} decorated classes and {len(functions)} decorated functions in {module_name} source")

        # Use registry information to enhance our findings
        from ..core import registry

        decorated_classes = []
        for class_name, class_info in registry.classes.items():
            if class_info.get('module') == module_name:
                cls = class_info.get('cls')
                if cls:
                    decorated_classes.append(cls)

        decorated_functions = []
        for func_name, func_info in registry.functions.items():
            if func_info.get('module') == module_name:
                func = func_info.get('func')
                if func:
                    decorated_functions.append(func)

        return decorated_classes, decorated_functions

    except Exception as e:
        print(f"Error during safe inspection of {module_name}: {str(e)}")
        return [], []