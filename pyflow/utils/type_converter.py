"""
Type conversion utilities for PyFlow.ts.
"""
import inspect
import typing
from typing import get_type_hints, Any, Dict, List, Set, Tuple, Optional, Union, Type

def _get_ts_type(py_type) -> str:
    """Convert a Python type to a TypeScript type."""
    if py_type is None or py_type == type(None):
        return "null"
    elif py_type == str:
        return "string"
    elif py_type == int or py_type == float:
        return "number"
    elif py_type == bool:
        return "boolean"
    elif py_type == dict or py_type == Dict:
        return "Record<string, any>"
    elif py_type == list or py_type == List:
        return "any[]"
    elif py_type == set or py_type == Set:
        return "Set<any>"
    elif py_type == tuple or py_type == Tuple:
        return "any[]"
    elif hasattr(py_type, '__origin__'):
        # Handle typing generics like List[str], Dict[str, int], etc.
        origin = py_type.__origin__
        if origin == list or origin == List:
            if hasattr(py_type, '__args__') and py_type.__args__:
                arg_type = _get_ts_type(py_type.__args__[0])
                return f"{arg_type}[]"
            return "any[]"
        elif origin == dict or origin == Dict:
            if hasattr(py_type, '__args__') and len(py_type.__args__) == 2:
                key_type = _get_ts_type(py_type.__args__[0])
                value_type = _get_ts_type(py_type.__args__[1])
                if key_type == "string":
                    return f"Record<string, {value_type}>"
                return f"Map<{key_type}, {value_type}>"
            return "Record<string, any>"
        elif origin == Union:
            if hasattr(py_type, '__args__'):
                # Handle Optional[Type] => Type | null
                if len(py_type.__args__) == 2 and type(None) in py_type.__args__:
                    other_type = [t for t in py_type.__args__ if t is not type(None)][0]
                    return f"{_get_ts_type(other_type)} | null"
                # Regular union type
                union_types = [_get_ts_type(arg) for arg in py_type.__args__]
                return " | ".join(union_types)
            return "any"
        elif origin == tuple or origin == Tuple:
            if hasattr(py_type, '__args__') and py_type.__args__:
                tuple_types = [_get_ts_type(arg) for arg in py_type.__args__]
                return f"[{', '.join(tuple_types)}]"
            return "any[]"
    elif py_type == Any:
        return "any"
    elif py_type == inspect._empty:
        return "any"
    elif hasattr(py_type, "__name__"):
        # Class types
        return py_type.__name__

    # Default to any for types we don't recognize
    return "any"

def generate_ts_interface(cls: Type) -> str:
    """Generate a TypeScript interface from a Python class."""
    class_name = cls.__name__

    # Extract class variables with type annotations
    properties = []
    for name, annotation in getattr(cls, "__annotations__", {}).items():
        if not name.startswith('_'):  # Skip private attributes
            ts_type = _get_ts_type(annotation)
            properties.append(f"  {name}: {ts_type};")

    # Extract methods
    methods = []
    for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
        if not name.startswith('_') or name == '__init__':  # Include __init__ but skip other private methods
            # Skip the method if it's decorated with @staticmethod or @classmethod
            if hasattr(method, "__self__") and (method.__self__ is cls or isinstance(method.__self__, type)):
                continue

            # Get return type hint
            return_type_hint = "any"
            try:
                hints = get_type_hints(method)
                if "return" in hints:
                    return_type_hint = _get_ts_type(hints["return"])
            except (TypeError, NameError):
                pass  # Use default return_type if we can't determine it

            # Get parameters
            signature = inspect.signature(method)
            params = []
            for param_name, param in signature.parameters.items():
                if param_name == 'self':
                    continue

                # Try to get type from type hint
                param_type = "any"
                try:
                    if param_name in hints:
                        param_type = _get_ts_type(hints[param_name])
                except (TypeError, NameError, KeyError):
                    pass

                # Handle default values for optional parameters - use `is not` instead of `!=`
                # to avoid triggering custom __ne__ methods
                try:
                    has_default = param.default is not param.empty
                except (TypeError, AttributeError):
                    # Handle case where comparison fails
                    has_default = False

                if has_default:
                    params.append(f"{param_name}?: {param_type}")
                else:
                    params.append(f"{param_name}: {param_type}")

            params_str = ", ".join(params)
            methods.append(f"  {name}({params_str}): Promise<{return_type_hint}>;")

    # Generate interface code
    ts_interface = f"export interface {class_name} {{\n"
    if properties:
        ts_interface += "\n".join(properties) + "\n"
    if methods:
        ts_interface += "\n".join(methods) + "\n"
    ts_interface += "}\n"

    return ts_interface

def generate_ts_class(cls: Type) -> str:
    """Generate a TypeScript class from a Python class."""
    class_name = cls.__name__

    # Start the class definition
    ts_class = f"export class {class_name} {{\n\n"

    # Add private fields for constructor args and instance ID
    ts_class += "  private _constructorArgs: any;\n"
    ts_class += "  private _instanceId: string | null = null;\n\n"

    # Add instance management methods
    ts_class += "  private async _ensureInstance(): Promise<void> {\n"
    ts_class += "    if (!this._instanceId) {\n"
    ts_class += "      this._instanceId = await pyflowRuntime.createInstance(this.constructor.name, this._constructorArgs);\n"
    ts_class += "    }\n"
    ts_class += "  }\n\n"

    ts_class += "  private async _callPythonMethod(methodName: string, args: any): Promise<any> {\n"
    ts_class += "    // Ensure we have an instance ID before calling methods\n"
    ts_class += "    await this._ensureInstance();\n"
    ts_class += "    // Call the method on our specific instance\n"
    ts_class += "    return pyflowRuntime.callMethod(this.constructor.name, methodName, args, this._constructorArgs);\n"
    ts_class += "  }\n\n"

    # Generate constructor
    constructor_params = []
    constructor_body = []

    # Initialize constructor args object
    constructor_body.append("    this._constructorArgs = {};")
    constructor_body.append("    this._constructorArgs['_module'] = 'symai.components';")

    # Get constructor parameters
    init_method = getattr(cls, "__init__", None)
    if init_method and hasattr(init_method, "__code__"):
        signature = inspect.signature(init_method)
        hints = {}
        try:
            hints = get_type_hints(init_method)
        except (TypeError, NameError):
            pass

        for param_name, param in signature.parameters.items():
            if param_name == 'self':
                continue

            if param_name == 'kwargs' or param.kind == param.VAR_KEYWORD:
                # Handle **kwargs specially - make it optional
                constructor_params.append("kwargs?: any")
                continue

            param_type = "any"
            try:
                if param_name in hints:
                    param_type = _get_ts_type(hints[param_name])
            except (TypeError, NameError):
                pass

            # Handle default values - use `is not` instead of `!=`
            try:
                has_default = param.default is not param.empty
            except (TypeError, AttributeError):
                has_default = False

            if has_default:
                default_value = param.default
                if default_value is None:
                    default_str = "null"
                elif default_value is False:
                    default_str = "false"
                elif default_value is True:
                    default_str = "true"
                elif isinstance(default_value, (int, float)):
                    default_str = str(default_value)
                elif isinstance(default_value, str):
                    default_str = f"'{default_value}'"
                elif isinstance(default_value, (list, dict, set, tuple)):
                    if not default_value:  # Empty container
                        if isinstance(default_value, list):
                            default_str = "[]"
                        elif isinstance(default_value, dict):
                            default_str = "{}"
                        elif isinstance(default_value, set):
                            default_str = "new Set()"
                        elif isinstance(default_value, tuple):
                            default_str = "[]"
                    else:
                        # For non-empty containers, it's safer to use undefined
                        default_str = "undefined"
                else:
                    # For any other type, use undefined
                    default_str = "undefined"

                # Add as optional parameter with default
                constructor_params.append(f"{param_name}: {param_type} = {default_str}")

                # Store parameter in constructor args and as instance property
                constructor_body.append(f"    this._constructorArgs['{param_name}'] = {param_name};")
                constructor_body.append(f"    this.{param_name} = {param_name}{' || null' if param_type.endswith('| null') else ''};")
            else:
                # Required parameter
                constructor_params.append(f"{param_name}: {param_type}")

                # Store parameter in constructor args and as instance property
                constructor_body.append(f"    this._constructorArgs['{param_name}'] = {param_name};")
                constructor_body.append(f"    this.{param_name} = {param_name};")
    else:
        # Default constructor with no parameters if __init__ is not defined
        constructor_params = []

    # Add constructor to class
    ts_class += f"  constructor({', '.join(constructor_params)}) {{\n"
    ts_class += "\n".join(constructor_body) + "\n"
    ts_class += "  }\n\n"

    # Generate methods
    for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
        if name != '__init__' and not name.startswith('_'):  # Skip private methods and constructor
            # Skip the method if it's decorated with @staticmethod or @classmethod
            if hasattr(method, "__self__") and (method.__self__ is cls or isinstance(method.__self__, type)):
                continue

            # Get return type hint
            return_type_hint = "any"
            try:
                hints = get_type_hints(method)
                if "return" in hints:
                    return_type_hint = _get_ts_type(hints["return"])
            except (TypeError, NameError):
                pass

            # Get parameters
            signature = inspect.signature(method)
            param_list = []
            args_dict = []

            for param_name, param in signature.parameters.items():
                if param_name == 'self':
                    continue

                # Try to get type from type hint
                param_type = "any"
                try:
                    if param_name in hints:
                        param_type = _get_ts_type(hints[param_name])
                except (TypeError, NameError, KeyError):
                    pass

                # Handle special parameter kinds
                if param_name == 'kwargs' or param.kind == param.VAR_KEYWORD:
                    param_list.append(f"{param_name}?: any")
                    continue

                # Handle default values for optional parameters - use `is not` instead of `!=`
                try:
                    has_default = param.default is not param.empty
                except (TypeError, AttributeError):
                    has_default = False

                if has_default:
                    default_value = param.default
                    if default_value is None:
                        default_str = "null"
                    elif default_value is False:
                        default_str = "false"
                    elif default_value is True:
                        default_str = "true"
                    elif isinstance(default_value, (int, float)):
                        default_str = str(default_value)
                    elif isinstance(default_value, str):
                        default_str = f"'{default_value}'"
                    else:
                        # For complex types, just use empty arrays/objects
                        if isinstance(default_value, list):
                            default_str = "[]"
                        elif isinstance(default_value, dict):
                            default_str = "{}"
                        else:
                            default_str = "undefined"

                    param_list.append(f"{param_name}: {param_type} = {default_str}")
                else:
                    param_list.append(f"{param_name}: {param_type}")

                # Add parameter to args dictionary
                args_dict.append(f"{param_name}: {param_name}")

            # Generate method code
            ts_class += f"  async {name}({', '.join(param_list)}): Promise<{return_type_hint}> {{\n"
            ts_class += "    // This is where the real implementation would call the Python backend\n"
            ts_class += f"    return this._callPythonMethod('{name}', {{{', '.join(args_dict)}}});\n"
            ts_class += "  }\n\n"

    # Close the class
    ts_class += "}"
    return ts_class

def generate_ts_function(func) -> str:
    """Generate a TypeScript function from a Python function."""
    func_name = func.__name__

    # Get return type hint
    return_type_hint = "any"
    try:
        hints = get_type_hints(func)
        if "return" in hints:
            return_type_hint = _get_ts_type(hints["return"])
    except (TypeError, NameError):
        pass

    # Get parameters
    signature = inspect.signature(func)
    param_list = []
    args_dict = []

    for param_name, param in signature.parameters.items():
        # Try to get type from type hint
        param_type = "any"
        try:
            if param_name in hints:
                param_type = _get_ts_type(hints[param_name])
        except (TypeError, NameError, KeyError):
            pass

        # Handle special parameter kinds
        if param_name == 'kwargs' or param.kind == param.VAR_KEYWORD:
            param_list.append(f"{param_name}?: any")
            continue

        # Handle default values for optional parameters - use `is not` instead of `!=`
        try:
            has_default = param.default is not param.empty
        except (TypeError, AttributeError):
            has_default = False

        if has_default:
            default_value = param.default
            if default_value is None:
                default_str = "null"
            elif default_value is False:
                default_str = "false"
            elif default_value is True:
                default_str = "true"
            elif isinstance(default_value, (int, float)):
                default_str = str(default_value)
            elif isinstance(default_value, str):
                default_str = f"'{default_value}'"
            else:
                # For complex types, just use empty arrays/objects
                if isinstance(default_value, list):
                    default_str = "[]"
                elif isinstance(default_value, dict):
                    default_str = "{}"
                else:
                    default_str = "undefined"

            param_list.append(f"{param_name}: {param_type} = {default_str}")
        else:
            param_list.append(f"{param_name}: {param_type}")

        # Add parameter to args dictionary
        args_dict.append(f"{param_name}: {param_name}")

    # Generate function code
    func_code = f"export async function {func_name}({', '.join(param_list)}): Promise<{return_type_hint}> {{\n"
    func_code += f"  return pyflowRuntime.callFunction('{func.__module__}', '{func_name}', {{{', '.join(args_dict)}}});\n"
    func_code += "}\n"

    return func_code

def generate_ts_type(cls: Type) -> str:
    """Generate TypeScript type definition for a Python class without implementation."""
    return generate_ts_interface(cls)

# Aliases for backward compatibility
python_type_to_ts_type = _get_ts_type
