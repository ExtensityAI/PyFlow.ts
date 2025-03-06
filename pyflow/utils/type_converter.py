"""
Type conversion utilities for PyFlow.ts.
"""
import inspect
import typing
from typing import Any, Dict, List, Set, Tuple, Type, Union, Optional, get_type_hints
import datetime as dt

def python_type_to_ts(python_type) -> str:
    """Convert a Python type to TypeScript type."""
    # Handle None, NoneType
    if python_type is type(None) or python_type is None:
        return "null"

    # Handle basic types
    if python_type is str:
        return "string"
    elif python_type is int or python_type is float:
        return "number"
    elif python_type is bool:
        return "boolean"
    elif python_type is list or python_type is List:
        return "any[]"
    elif python_type is dict or python_type is Dict:
        return "Record<string, any>"
    elif python_type is set or python_type is Set:
        return "Set<any>"
    elif python_type is tuple or python_type is Tuple:
        return "any[]"  # TypeScript doesn't have tuples in the same way
    elif python_type is Any or python_type is object:
        return "any"

    # Handle standard library types
    # Check for datetime and date types
    if python_type is dt.datetime or str(python_type).endswith('.datetime'):
        return "Date"
    elif python_type is dt.date or str(python_type).endswith('.date'):
        return "Date"
    elif python_type is dt.time or str(python_type).endswith('.time'):
        return "string"  # Time as string in ISO format

    # Handle generic types (List[T], Dict[K,V], etc.)
    origin = getattr(python_type, "__origin__", None)
    if origin:
        args = getattr(python_type, "__args__", [])

        if origin is list or origin is List:
            if args:
                arg_type = python_type_to_ts(args[0])
                return f"{arg_type}[]"
            return "any[]"

        elif origin is dict or origin is Dict:
            if len(args) >= 2:
                key_type = python_type_to_ts(args[0])
                val_type = python_type_to_ts(args[1])
                if key_type == "string" or key_type == "number":
                    return f"Record<{key_type}, {val_type}>"
                return f"Map<{key_type}, {val_type}>"
            return "Record<string, any>"

        elif origin is Union:
            # Handle Optional[T] which is Union[T, None]
            if len(args) == 2 and args[1] is type(None):
                return f"{python_type_to_ts(args[0])} | null"

            # Regular union type
            types = [python_type_to_ts(arg) for arg in args]
            return " | ".join(types)

        elif origin is Optional:
            if args:
                return f"{python_type_to_ts(args[0])} | null"
            return "any | null"

        elif origin is set or origin is Set:
            if args:
                arg_type = python_type_to_ts(args[0])
                return f"Set<{arg_type}>"
            return "Set<any>"

        elif origin is tuple or origin is Tuple:
            if args:
                arg_types = [python_type_to_ts(arg) for arg in args]
                return f"[{', '.join(arg_types)}]"
            return "any[]"

    # Try to handle classes by name
    if inspect.isclass(python_type):
        # Check for common library types by name
        name = python_type.__name__
        module = getattr(python_type, "__module__", "")

        # Handle common standard library types
        if module == 'datetime' or module.endswith('.datetime'):
            if name == 'datetime':
                return "Date"
            elif name == 'date':
                return "Date"
            elif name == 'time':
                return "string"

        return name

    # Default fallback
    return "any"

def generate_ts_interface(cls: Type) -> str:
    """Generate TypeScript interface from a Python class."""
    class_name = cls.__name__

    # Get type hints for class attributes
    try:
        attrs = get_type_hints(cls)
    except (TypeError, NameError):
        attrs = {}

    # Add instance variables from __init__ method
    if hasattr(cls, "__init__") and cls.__init__ is not object.__init__:
        try:
            init_hints = get_type_hints(cls.__init__)
            # Remove 'self' and 'return'
            init_hints.pop('self', None)
            init_hints.pop('return', None)
            # Merge with class attrs
            attrs.update(init_hints)
        except (TypeError, NameError):
            pass

    # Build the interface string
    lines = [f"export interface {class_name} {{"]

    # Add attributes
    for attr_name, attr_type in attrs.items():
        if not attr_name.startswith('_'):  # Skip private attributes
            ts_type = python_type_to_ts(attr_type)
            lines.append(f"  {attr_name}: {ts_type};")

    # Add declared methods (not including inherited methods)
    for name, method in inspect.getmembers(cls, inspect.isfunction):
        if name.startswith('_') and name != '__init__':
            continue  # Skip private/special methods except __init__

        try:
            method_hints = get_type_hints(method)
            params = list(inspect.signature(method).parameters.items())

            if params and params[0][0] == 'self':
                params = params[1:]  # Remove 'self' parameter

            param_strings = []
            for param_name, param in params:
                if param_name in method_hints:
                    param_type = python_type_to_ts(method_hints[param_name])
                else:
                    param_type = "any"

                if param.default is not inspect.Parameter.empty:
                    param_strings.append(f"{param_name}?: {param_type}")
                else:
                    param_strings.append(f"{param_name}: {param_type}")

            return_type = "any"
            if "return" in method_hints and method_hints["return"] is not type(None):
                return_type = python_type_to_ts(method_hints["return"])

            lines.append(f"  {name}({', '.join(param_strings)}): {return_type};")
        except (TypeError, ValueError):
            # Skip methods with invalid signatures
            pass

    lines.append("}")
    return "\n".join(lines)

def generate_ts_class(cls: Type) -> str:
    """Generate TypeScript class from a Python class."""
    class_name = cls.__name__

    # Check if this class has decorated methods
    has_decorated_methods = False
    for name, method in inspect.getmembers(cls, inspect.isfunction):
        if getattr(method, '_pyflow_decorated', False):
            has_decorated_methods = True
            break

    # If no decorated methods, use the simple class approach
    if not has_decorated_methods and not getattr(cls, '_pyflow_decorated', False):
        return f"""export class {class_name} {{
  // This class has no decorated methods, only the interface is used
}}"""

    # Build the class string
    lines = [f"export class {class_name} {{"]

    # Get all properties from the interface
    try:
        attrs = get_type_hints(cls)
    except (TypeError, NameError):
        attrs = {}

    # Add instance variables from __init__
    if hasattr(cls, "__init__") and cls.__init__ is not object.__init__:
        try:
            init_hints = get_type_hints(cls.__init__)
            init_hints.pop('self', None)
            init_hints.pop('return', None)
            attrs.update(init_hints)
        except (TypeError, NameError):
            pass

    # Add property declarations
    for attr_name, attr_type in attrs.items():
        if not attr_name.startswith('_'):  # Skip private attributes
            ts_type = python_type_to_ts(attr_type)
            lines.append(f"  {attr_name}: {ts_type};")

    # Add constructor
    lines.append(f"  constructor(args: Partial<{class_name}> = {{}}) {{")
    lines.append("    Object.assign(this, args);")
    lines.append("  }")
    lines.append("")

    # Add decorated methods
    for name, method in inspect.getmembers(cls, inspect.isfunction):
        if name.startswith('_') and name != '__init__':
            continue  # Skip private/special methods except __init__

        # Include all methods in the class implementation
        try:
            method_hints = get_type_hints(method)
            params = list(inspect.signature(method).parameters.items())

            if params and params[0][0] == 'self':
                params = params[1:]  # Remove 'self' parameter

            param_strings = []
            param_names = []
            for param_name, param in params:
                if param_name in method_hints:
                    param_type = python_type_to_ts(method_hints[param_name])
                else:
                    param_type = "any"

                if param.default is not inspect.Parameter.empty:
                    param_strings.append(f"{param_name}?: {param_type}")
                else:
                    param_strings.append(f"{param_name}: {param_type}")

                param_names.append(param_name)

            return_type = "any"
            if "return" in method_hints and method_hints["return"] is not type(None):
                return_type = python_type_to_ts(method_hints["return"])

            # Generate method implementation based on whether it's decorated
            if getattr(method, '_pyflow_decorated', False):
                lines.append(f"  async {name}({', '.join(param_strings)}): Promise<{return_type}> {{")
                lines.append(f"    return pyflowRuntime.callMethod(")
                lines.append(f"      '{class_name}',")
                lines.append(f"      '{name}',")
                lines.append(f"      {{{', '.join(f'{pname}: {pname}' for pname in param_names)}}},")
                lines.append(f"      {{}}")
                lines.append(f"    );")
                lines.append(f"  }}")
            else:
                # For non-decorated methods, provide a stub implementation
                lines.append(f"  {name}({', '.join(param_strings)}): {return_type} {{")
                if return_type != "void":
                    lines.append(f"    throw new Error('Method {name} not implemented');")
                lines.append(f"  }}")

            lines.append("")
        except (TypeError, ValueError):
            # Skip methods with invalid signatures
            pass

    lines.append(f"  static async createInstance(args: Partial<{class_name}> = {{}}): Promise<{class_name}> {{")
    lines.append(f"    const instance = new {class_name}(args);")
    lines.append(f"    await pyflowRuntime.createInstance('{class_name}', args);")
    lines.append("    return instance;")
    lines.append("  }")

    lines.append("}")

    # Add type alias to make usage cleaner
    lines.append(f"\n// Type alias for implementation class")
    lines.append(f"export type {class_name}Type = {class_name};")

    return "\n".join(lines)

def generate_ts_function(func) -> str:
    """Generate TypeScript function from a Python function."""
    func_name = func.__name__
    module_name = func.__module__

    try:
        hints = get_type_hints(func)
        params = list(inspect.signature(func).parameters.items())

        param_strings = []
        param_names = []
        for param_name, param in params:
            if param_name in hints:
                param_type = python_type_to_ts(hints[param_name])
            else:
                param_type = "any"

            if param.default is not inspect.Parameter.empty:
                param_strings.append(f"{param_name}?: {param_type}")
            else:
                param_strings.append(f"{param_name}: {param_type}")

            param_names.append(param_name)

        return_type = "any"
        if "return" in hints:
            if hints["return"] is not type(None):
                return_type = python_type_to_ts(hints["return"])

        # Generate function docstring as comment
        doc = inspect.getdoc(func) or ""
        doc_comment = ""
        if doc:
            lines = doc.split("\n")
            doc_comment = "/**\n"
            for line in lines:
                doc_comment += f" * {line}\n"
            doc_comment += " */\n"

        return f"""{doc_comment}export async function {func_name}({', '.join(param_strings)}): Promise<{return_type}> {{
  return pyflowRuntime.callFunction(
    '{module_name}',
    '{func_name}',
    {{{', '.join(f'{pname}: {pname}' for pname in param_names)}}}
  );
}}"""
    except Exception as e:
        print(f"Error generating TypeScript function for {func_name}: {str(e)}")
        return f"// Error generating TypeScript for function {func_name}: {str(e)}"

def generate_ts_type(cls: Type) -> str:
    """Generate TypeScript type definition for a class."""
    # Use interface generation for non-decorated classes
    return generate_ts_interface(cls)
