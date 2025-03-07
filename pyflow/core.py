"""
Core functionality for the PyFlow.ts library.
"""
import inspect
import importlib
import importlib.util
import sys
import os
from pathlib import Path
from typing import Any, Callable, Type, get_type_hints

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

        # Also register parent modules to ensure proper generation
        parts = module_name.split('.')
        for i in range(1, len(parts)):
            parent_module = '.'.join(parts[:i])
            self.modules.add(parent_module)

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

        # Also register parent modules to ensure proper generation
        parts = module_name.split('.')
        for i in range(1, len(parts)):
            parent_module = '.'.join(parts[:i])
            self.modules.add(parent_module)

registry = Registry()

def extensity(cls_or_func):
    """Decorator to mark a class or function for PyFlow.ts generation."""
    if inspect.isclass(cls_or_func):
        cls = cls_or_func
        module_name = cls.__module__

        # Mark class as decorated
        setattr(cls, '_pyflow_decorated', True)

        # Register the class with the registry
        registry.register_class(cls, module_name)
        return cls

    elif inspect.isfunction(cls_or_func):
        func = cls_or_func
        module_name = func.__module__

        # Mark function as decorated
        setattr(func, '_pyflow_decorated', True)

        # Register the function with the registry
        registry.register_function(func, module_name)
        return func

    else:
        raise TypeError("@extensity can only be used on classes and functions")

def import_module_from_path(module_path: str) -> Any:
    """Import a module from a dotted path or a file path."""
    # Remove trailing slashes for consistent handling
    if (module_path.endswith('/')):
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

def try_import_module(file_path, module_options, imported_modules):
    """Helper function to try importing a module with various strategies."""
    success = False

    try:
        # Import the module - try different approaches
        initial_registry_size = len(registry.modules)

        # Try each module name option
        for full_module_name in module_options:
            # First try as a submodule of the directory
            try:
                module = importlib.import_module(full_module_name)
                success = True
                break
            except (ModuleNotFoundError, ImportError, AttributeError) as e:
                if "Conversation" in str(e) and "not defined" in str(e):
                    # Skip modules with dependency errors for now
                    print(f"⏳ Skipping module with dependency error: {str(e)}")
                    return False
                continue

        # If normal import fails, try direct file import
        if not success:
            try:
                # Use spec_from_file_location as a last resort
                module_name = module_options[0]
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)
                    success = True
            except (ImportError, ModuleNotFoundError, AttributeError) as e:
                # Skip any import that fails due to missing dependencies
                if "Conversation" in str(e) and "not defined" in str(e):
                    print(f"⏳ Skipping module with dependency error: {str(e)}")
                else:
                    print(f"❌ Error importing module: {str(e)}")
                return False

        # Check if module contains PyFlow.ts decorators
        if success and len(registry.modules) > initial_registry_size:
            # Use the module name that was successfully imported
            imported_name = module.__name__
            imported_modules.append(imported_name)
            print(f"✅ Found PyFlow.ts decorators in: {imported_name}")
            return True
        elif success:
            print(f"ℹ️ No PyFlow.ts decorators found in: {module.__name__}")
            return True

    except Exception as e:
        print(f"❌ Error importing module: {str(e)}")

    return False
