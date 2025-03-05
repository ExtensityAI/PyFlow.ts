"""
Type conversion utilities between Python and TypeScript.
"""
import inspect
from typing import (
    Any, Dict, FrozenSet, List, Set, Tuple, Union, Optional,
    Callable, Type, get_origin, get_args, get_type_hints
)
import datetime
import uuid

def python_type_to_ts_type(py_type: Any) -> str:
    """
    Convert a Python type to a TypeScript type.

    Args:
        py_type: Python type annotation

    Returns:
        Equivalent TypeScript type as a string
    """
    # Handle None/NoneType explicitly
    if py_type is None or py_type is type(None):
        return "null"

    # Handle primitive types
    if py_type is str:
        return "string"
    elif py_type is int or py_type is float:
        return "number"
    elif py_type is bool:
        return "boolean"
    elif py_type is bytes or py_type is bytearray:
        return "Uint8Array"
    elif py_type is complex:
        return "{ re: number, im: number }"

    # Handle Any
    elif py_type is Any:
        return "any"

    # Handle collections
    elif py_type is list:
        return "any[]"
    elif py_type is dict:
        return "Record<string, any>"
    elif py_type is tuple:
        return "any[]"
    elif py_type is set or py_type is frozenset:
        return "Set<any>"

    # Handle common types
    elif py_type is datetime.datetime:
        return "string"  # ISO format string
    elif py_type is datetime.date:
        return "string"  # ISO format string
    elif py_type is uuid.UUID:
        return "string"

    # Handle generic types from typing module
    origin = get_origin(py_type)
    args = get_args(py_type)

    if origin is not None:
        # Handle Union and Optional
        if origin is Union:
            # Special case for Optional[T] which is Union[T, None]
            if len(args) == 2 and args[1] is type(None):
                return f"{python_type_to_ts_type(args[0])} | null"
            # Regular Union
            return " | ".join(python_type_to_ts_type(arg) for arg in args)

        # Handle List, Set, etc.
        elif origin is list or origin is List:
            if args:
                return f"{python_type_to_ts_type(args[0])}[]"
            return "any[]"

        # Handle Dict
        elif origin is dict or origin is Dict:
            if len(args) >= 2:
                key_type, val_type = args[:2]
                # TypeScript only supports string, number, or symbol as keys
                if key_type is str:
                    return f"Record<string, {python_type_to_ts_type(val_type)}>"
                elif key_type is int:
                    return f"Record<number, {python_type_to_ts_type(val_type)}>"
                else:
                    return f"Record<string, {python_type_to_ts_type(val_type)}>"
            return "Record<string, any>"

        # Handle Tuple
        elif origin is tuple or origin is Tuple:
            if args:
                # Handle specific tuple types like Tuple[str, int]
                if Ellipsis not in args:
                    return f"[{', '.join(python_type_to_ts_type(arg) for arg in args)}]"
                # Handle variadic tuples like Tuple[str, ...]
                else:
                    return f"{python_type_to_ts_type(args[0])}[]"
            return "any[]"

        # Handle Set
        elif origin is set or origin is Set or origin is frozenset or origin is FrozenSet:
            if args:
                return f"Set<{python_type_to_ts_type(args[0])}>"
            return "Set<any>"

        # Handle Optional - redundant but explicit
        elif origin is Optional:
            return f"{python_type_to_ts_type(args[0])} | null"

    # Handle classes (assuming they will be exported as interfaces)
    if inspect.isclass(py_type):
        return py_type.__name__

    # Default fallback
    return "any"

def generate_ts_interface(cls: Type) -> str:
    """
    Generate a TypeScript interface from a Python class.

    Args:
        cls: Python class

    Returns:
        TypeScript interface definition
    """
    properties = []

    # Add class variables with type annotations
    for name, type_hint in getattr(cls, '__annotations__', {}).items():
        ts_type = python_type_to_ts_type(type_hint)
        properties.append(f"  {name}: {ts_type};")

    # Generate the interface
    interface = f"export interface {cls.__name__} {{\n"
    interface += "\n".join(properties)
    interface += "\n}"

    return interface

def generate_ts_class(cls: Type) -> str:
    """
    Generate a TypeScript class from a Python class.

    Args:
        cls: Python class

    Returns:
        TypeScript class definition
    """
    properties = []
    methods = []
    constructor_params = []
    constructor_body = []
    property_initializers = {}  # Track property initializers
    properties_initialized_at_class_level = set()  # Track properties already initialized at class level

    # Add class variables with type annotations
    for name, type_hint in getattr(cls, '__annotations__', {}).items():
        ts_type = python_type_to_ts_type(type_hint)

        # Determine appropriate default value based on type
        default_value = None
        if ts_type.endswith('[]'):
            default_value = "[]"  # Empty array for array types
        elif ts_type == "Record<string, any>" or ts_type.startswith("Record<"):
            default_value = "{}"  # Empty object for record types
        elif ts_type == "string":
            default_value = "''"  # Empty string for string types
        elif ts_type == "number":
            default_value = "0"   # Zero for number types
        elif ts_type == "boolean":
            default_value = "false"  # False for boolean types
        elif "| null" in ts_type:
            default_value = "null"  # Null for nullable types

        # Add initializer for property if appropriate
        if default_value is not None:
            property_initializers[name] = default_value
            properties.append(f"  {name}: {ts_type} = {default_value};")
            # Mark as initialized at class level to avoid redundancy in constructor
            properties_initialized_at_class_level.add(name)
        else:
            properties.append(f"  {name}: {ts_type};")

        # Set default value if available from Python class
        if hasattr(cls, name):
            value = getattr(cls, name)
            if isinstance(value, str):
                constructor_body.append(f"    this.{name} = '{value}';")
            elif value is None:
                constructor_body.append(f"    this.{name} = null;")
            else:
                constructor_body.append(f"    this.{name} = {value};")

    # Add methods
    for name, method in inspect.getmembers(cls, inspect.isfunction):
        if name.startswith('_') and name != '__init__':
            continue

        signature = inspect.signature(method)
        type_hints = get_type_hints(method)

        if name == '__init__':
            # Handle constructor
            for param_name, param in signature.parameters.items():
                if param_name == 'self':
                    continue

                param_type = type_hints.get(param_name, Any)
                ts_type = python_type_to_ts_type(param_type)

                if param.default is not inspect.Parameter.empty:
                    if isinstance(param.default, str):
                        constructor_params.append(f"{param_name}: {ts_type} = '{param.default}'")
                    elif param.default is None:
                        constructor_params.append(f"{param_name}: {ts_type} = null")
                    else:
                        constructor_params.append(f"{param_name}: {ts_type} = {param.default}")
                else:
                    constructor_params.append(f"{param_name}: {ts_type}")

                constructor_body.append(f"    this.{param_name} = {param_name};")
        else:
            # Regular method
            method_params = []
            for param_name, param in signature.parameters.items():
                if param_name == 'self':
                    continue

                param_type = type_hints.get(param_name, Any)
                ts_type = python_type_to_ts_type(param_type)

                if param.default is not inspect.Parameter.empty:
                    if isinstance(param.default, str):
                        method_params.append(f"{param_name}: {ts_type} = '{param.default}'")
                    elif param.default is None:
                        method_params.append(f"{param_name}: {ts_type} = null")
                    else:
                        method_params.append(f"{param_name}: {ts_type} = {param.default}")
                else:
                    method_params.append(f"{param_name}: {ts_type}")

            return_type = type_hints.get('return', Any)
            ts_return_type = python_type_to_ts_type(return_type)

            # Fix: Handle "null" return type properly
            cast_type = ts_return_type
            if ts_return_type == "null":
                cast_type = "void"

            # Fix: Build method arguments object without duplicate method name
            method_args = "{}"
            if method_params:
                method_args = "{" + ", ".join(param_name + ": " + param_name for param_name, _ in (p.split(':', 1) for p in method_params)) + "}"

            method_body = f"    // This is where the real implementation would call the Python backend\n"
            # Fix: Only pass method name once, followed by the args object
            method_body += f"    return this._callPythonMethod('{name}', {method_args});"

            methods.append(f"  {name}({', '.join(method_params)}): {ts_return_type} {{\n{method_body}\n  }}")

    # Generate the constructor with proper initialization for nullable properties
    constructor = f"  constructor({', '.join(constructor_params)}) {{\n"

    # Initialize the constructor body with proper _constructorArgs initialization
    constructor_body = []

    # First initialize _constructorArgs as an empty object - this must happen first
    constructor_body.append("    this._constructorArgs = {};")

    # Store module information to help with instance creation
    module_name = getattr(cls, "__module__", "")
    if module_name:
        constructor_body.append(f"    this._constructorArgs['_module'] = '{module_name}';")

    # Check if we have any valid parameters before trying to process them
    has_params = False
    for param_name, param in inspect.signature(cls.__init__).parameters.items():
        if param_name != 'self' and param.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            has_params = True
            break

    # Only process parameters if there are valid ones
    if has_params:
        # Process each parameter
        for param_name, param in inspect.signature(cls.__init__).parameters.items():
            if param_name == 'self':
                continue

            # Skip variadic arguments like *args and **kwargs
            if param.kind == inspect.Parameter.VAR_POSITIONAL or param.kind == inspect.Parameter.VAR_KEYWORD:
                continue

            # Add to _constructorArgs using bracket notation to avoid undefined references
            constructor_body.append(f"    this._constructorArgs['{param_name}'] = {param_name};")

            # Initialize instance property with proper null handling
            type_hints = get_type_hints(cls.__init__)
            param_type = type_hints.get(param_name, Any)
            ts_type = python_type_to_ts_type(param_type)

            if '| null' in ts_type and param.default is None:
                constructor_body.append(f"    this.{param_name} = {param_name} || null;")
            else:
                constructor_body.append(f"    this.{param_name} = {param_name};")

    # For any class properties not already initialized in constructor or at class level,
    # initialize them in the constructor
    for name, default_value in property_initializers.items():
        # Only add to constructor if:
        # 1. Not already initialized in constructor by parameter assignment
        # 2. Not already initialized at class level
        if not any(f"this.{name} = " in line for line in constructor_body) and name not in properties_initialized_at_class_level:
            constructor_body.append(f"    this.{name} = {default_value};")

    # Join all the constructor body statements - now we're sure the body has at least the _constructorArgs initialization
    constructor += "\n".join(constructor_body)
    constructor += "\n  }"

    # Generate the class
    ts_class = f"export class {cls.__name__} {{\n"
    ts_class += "\n".join(properties) + "\n\n"
    ts_class += "  private _constructorArgs: any;\n"
    ts_class += "  private _instanceId: string | null = null;\n\n"

    ts_class += "  private async _ensureInstance(): Promise<void> {\n"
    ts_class += "    if (!this._instanceId) {\n"
    ts_class += "      this._instanceId = await pyflowRuntime.createInstance(this.constructor.name, this._constructorArgs);\n"
    ts_class += "      console.log(`Created new instance with ID: ${this._instanceId}`);\n"
    ts_class += "    }\n"
    ts_class += "  }\n\n"

    ts_class += "  private async _callPythonMethod(methodName: string, args: any): Promise<any> {\n"
    ts_class += "    // Ensure we have an instance ID before calling methods\n"
    ts_class += "    await this._ensureInstance();\n"
    ts_class += "    // Call the method on our specific instance\n"
    ts_class += "    return pyflowRuntime.callMethod(this.constructor.name, methodName, args, this._constructorArgs);\n"
    ts_class += "  }\n\n"

    ts_class += constructor + "\n\n"

    # Update all methods to be async
    updated_methods = []
    for method in methods:
        if not "async " in method:
            # Extract the method name and parameters
            method_parts = method.split("): ", 1)
            if len(method_parts) == 2:
                # Get the method signature and body
                signature = method_parts[0] + ")"  # e.g., "  method_name(param: type)"
                return_type_and_body = method_parts[1]  # e.g., "return_type {\n...body...}"

                # Split the return type and method body
                body_parts = return_type_and_body.split(" {", 1)
                if len(body_parts) == 2:
                    return_type = body_parts[0]  # e.g., "string"
                    body = "{" + body_parts[1]   # e.g., "{\n...body...}"

                    # Create the async method with Promise return type
                    async_method = signature + ": Promise<" + return_type + "> " + body

                    # Make it async
                    async_method = async_method.replace(signature, "  async " + signature.strip())

                    updated_methods.append(async_method)
                    continue

        # If we couldn't parse it or it's already async, keep the original
        updated_methods.append(method)

    ts_class += "\n\n".join(updated_methods)
    ts_class += "\n}"

    return ts_class

def generate_ts_function(func: Callable) -> str:
    """
    Generate a TypeScript function from a Python function.

    Args:
        func: Python function

    Returns:
        TypeScript function declaration
    """
    signature = inspect.signature(func)
    type_hints = get_type_hints(func)

    params = []
    for name, param in signature.parameters.items():
        param_type = type_hints.get(name, Any)
        ts_type = python_type_to_ts_type(param_type)

        if param.default is not inspect.Parameter.empty:
            if isinstance(param.default, str):
                params.append(f"{name}: {ts_type} = '{param.default}'")
            elif param.default is None:
                params.append(f"{name}: {ts_type} = null")
            else:
                params.append(f"{name}: {ts_type} = {param.default}")
        else:
            params.append(f"{name}: {ts_type}")

    return_type = type_hints.get('return', Any)
    ts_return_type = python_type_to_ts_type(return_type)

    func_body = f"  // This is where the real implementation would call the Python backend\n"
    func_body += f"  return pyflowRuntime.callFunction('{func.__module__}', '{func.__name__}', {{{ ', '.join(name + ': ' + name for name, _ in (p.split(':', 1) for p in params)) }}}) as {ts_return_type};"

    func_declaration = f"export function {func.__name__}({', '.join(params)}): {ts_return_type} {{\n{func_body}\n}}"

    return func_declaration

def generate_ts_type(cls: Type) -> str:
    """
    Generate a TypeScript type/interface from a Python class,
    even if the class itself is not decorated with @extensity.

    Args:
        cls: Python class

    Returns:
        TypeScript interface definition
    """
    properties = []

    # Add class variables with type annotations
    for name, type_hint in getattr(cls, '__annotations__', {}).items():
        ts_type = python_type_to_ts_type(type_hint)
        properties.append(f"  {name}: {ts_type};")

    # Generate the interface
    interface = f"export interface {cls.__name__} {{\n"
    interface += "\n".join(properties)
    interface += "\n}"

    return interface
