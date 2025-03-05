"""
Core functionality for the PyFlow.ts library.
"""
import inspect
import importlib
import importlib.util
import sys
import os
from pathlib import Path
from typing import Any, List, Callable, Type, get_type_hints

# Global registry to track decorated items
class Registry:
    """Registry for PyFlow.ts-decorated items."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Registry, cls).__new__(cls)
            cls._instance.functions = {}
            cls._instance.classes = {}
            cls._instance.modules = set()
        return cls._instance

    def register_function(self, func: Callable, module_name: str) -> None:
        """Register a function with the PyFlow.ts registry."""
        self.functions[func.__qualname__] = {
            'func': func,
            'module': module_name,
            'type_hints': get_type_hints(func),
            'signature': inspect.signature(func)
        }
        self.modules.add(module_name)

    def register_class(self, cls: Type, module_name: str) -> None:
        """Register a class with the PyFlow.ts registry."""
        methods = {}

        # Register methods
        for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
            # Only include public methods (not starting with underscore except __init__)
            if (not name.startswith('_') or name == '__init__') and getattr(method, '_pyflow_decorated', False) is False:
                methods[name] = {
                    'method': method,
                    'type_hints': get_type_hints(method),
                    'signature': inspect.signature(method)
                }

        # Register class variables with type annotations
        class_vars = {}
        for name, value in cls.__annotations__.items():
            # Only include public attributes (not starting with underscore)
            if not name.startswith('_'):
                if hasattr(cls, name):
                    class_vars[name] = {
                        'type': value,
                        'default': getattr(cls, name)
                    }
                else:
                    class_vars[name] = {
                        'type': value,
                        'default': None
                    }

        self.classes[cls.__qualname__] = {
            'cls': cls,
            'module': module_name,
            'methods': methods,
            'class_vars': class_vars
        }

        # Mark class as decorated to avoid redundancy
        setattr(cls, '_pyflow_decorated', True)

        # Keep track of which modules have decorated items
        self.modules.add(module_name)

registry = Registry()

def import_module_from_path(module_path: str) -> Any:
    """Import a module from a dotted path or a file path."""
    # Remove trailing slashes for consistent handling
    if module_path.endswith('/'):
        module_path = module_path.rstrip('/')

    # Check if it's a directory before attempting import
    if os.path.isdir(module_path):
        print(f"Warning: '{module_path}' is a directory. Use scan_directory() for directories.")
        return None

    # Handle case where path uses slashes instead of dots
    if '/' in module_path:
        # Convert file path to module path
        if module_path.endswith('.py'):
            module_path_clean = module_path[:-3].replace('/', '.')
        else:
            module_path_clean = module_path.replace('/', '.')
    else:
        module_path_clean = module_path

    try:
        # First, try to import as a regular module
        return importlib.import_module(module_path_clean)
    except ModuleNotFoundError:
        # If that fails, try to import from a file path
        if os.path.exists(module_path):
            # Get absolute path and directory
            abs_path = os.path.abspath(module_path)
            directory = os.path.dirname(abs_path)

            # Add directory to Python path temporarily
            if directory not in sys.path:
                sys.path.insert(0, directory)
                path_added = True
            else:
                path_added = False

            try:
                # Get module name from filename
                module_name = os.path.splitext(os.path.basename(module_path))[0]

                # Try to import the module
                spec = importlib.util.spec_from_file_location(module_name, abs_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)
                    return module
                else:
                    raise ImportError(f"Could not load module from {module_path}")
            finally:
                # Remove directory from Python path if we added it
                if path_added and directory in sys.path:
                    sys.path.remove(directory)
        else:
            # Try with .py extension if it wasn't specified
            py_path = module_path + '.py'
            if os.path.exists(py_path):
                return import_module_from_path(py_path)

        # If all fails, raise a more helpful error
        raise ImportError(f"Could not import module {module_path}")

def get_module_file_path(module_name: str) -> Path:
    """Get the file path for a module."""
    module = importlib.import_module(module_name)
    return Path(inspect.getfile(module))

def scan_directory(directory_path: str) -> List[str]:
    """
    Recursively scan a directory for Python modules and import them.

    Args:
        directory_path: Path to directory to scan

    Returns:
        List of imported module names
    """
    # Remove trailing slash for consistency
    directory_path = directory_path.rstrip('/')

    imported_modules = []

    # Convert to absolute path
    abs_path = os.path.abspath(directory_path)
    print(f"Scanning directory: {abs_path}")

    # Add directory to Python path temporarily if it's not already there
    parent_dir = os.path.dirname(abs_path)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
        parent_added = True
    else:
        parent_added = False

    if abs_path not in sys.path:
        sys.path.insert(0, abs_path)
        path_added = True
    else:
        path_added = False

    try:
        # Get just the directory name for module naming
        dir_name = os.path.basename(abs_path)

        # Walk the directory
        for root, dirs, files in os.walk(abs_path):
            # Skip generated and cache directories
            if 'generated' in root or '__pycache__' in root:
                continue

            # Get relative path for proper module naming
            rel_path = os.path.relpath(root, abs_path)
            if rel_path == '.':
                package_path = ''
            else:
                package_path = rel_path.replace(os.path.sep, '.')

            # Process all Python files
            for file in files:
                if file.endswith('.py') and not file.startswith('__'):
                    file_path = os.path.join(root, file)
                    print(f"Examining: {file_path}")

                    # Determine module name
                    module_name = os.path.splitext(file)[0]

                    if package_path:
                        full_module_name = f"{package_path}.{module_name}"
                    else:
                        full_module_name = module_name

                    try:
                        # Import the module
                        initial_registry_size = len(registry.modules)

                        # First try direct import
                        try:
                            module = importlib.import_module(full_module_name)
                        except ModuleNotFoundError:
                            # If direct import fails, try spec_from_file_location
                            spec = importlib.util.spec_from_file_location(full_module_name, file_path)
                            if spec and spec.loader:
                                module = importlib.util.module_from_spec(spec)
                                sys.modules[full_module_name] = module
                                spec.loader.exec_module(module)
                            else:
                                raise ImportError(f"Failed to import {file_path}")

                        # Check if module contains PyFlow.ts decorators
                        if len(registry.modules) > initial_registry_size:
                            imported_modules.append(full_module_name)
                            print(f"✅ Found PyFlow.ts decorators in: {full_module_name}")
                        else:
                            print(f"ℹ️ No PyFlow.ts decorators found in: {full_module_name}")

                    except Exception as e:
                        print(f"❌ Error importing module {full_module_name}: {str(e)}")

    finally:
        # Remove directories from Python path
        if path_added and abs_path in sys.path:
            sys.path.remove(abs_path)
        if parent_added and parent_dir in sys.path:
            sys.path.remove(parent_dir)

    if imported_modules:
        print(f"Found {len(imported_modules)} modules with PyFlow.ts decorators")
    else:
        print("No modules with PyFlow.ts decorators were found. Make sure you've added @extensity decorators to your functions or classes.")

    return imported_modules
