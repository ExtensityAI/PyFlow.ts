"""
Type conversion utilities for PyFlow.ts.
"""
import inspect
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

            # Separate required and optional parameters
            required_params = []
            optional_params = []

            for param_name, param in params:
                if param_name in method_hints:
                    param_type = python_type_to_ts(method_hints[param_name])
                else:
                    param_type = "any"

                if param.default is inspect.Parameter.empty:
                    required_params.append(f"{param_name}: {param_type}")
                else:
                    optional_params.append(f"{param_name}?: {param_type}")

            # Combine parameters with required first, then optional
            param_strings = required_params + optional_params

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

    # Check if this class has decorated methods or is itself decorated
    has_decorated_methods = False
    is_class_decorated = getattr(cls, '_pyflow_decorated', False)

    for name, method in inspect.getmembers(cls, inspect.isfunction):
        if getattr(method, '_pyflow_decorated', False):
            has_decorated_methods = True
            break

    # If no decorated methods and class not decorated, use the simple class approach
    if not has_decorated_methods and not is_class_decorated:
        return f"""export class {class_name} {{
  // This class has no decorated methods, only the interface is used
}}"""

    # Build the class string
    lines = [f"export class {class_name} {{"]

    # Add instance tracking property
    lines.append(f"  // Instance tracking")
    lines.append(f"  private _instanceId?: string;")

    # Get all properties from the interface
    try:
        attrs = get_type_hints(cls)
    except (TypeError, NameError):
        attrs = {}

    # Add instance variables from __init__
    init_params = []
    constructor_params = []
    constructor_assignments = []

    if hasattr(cls, "__init__") and cls.__init__ is not object.__init__:
        try:
            init_hints = get_type_hints(cls.__init__)
            init_hints.pop('self', None)
            init_hints.pop('return', None)

            # Extract required and optional parameters from __init__
            init_sig = inspect.signature(cls.__init__)
            for name, param in list(init_sig.parameters.items())[1:]:  # Skip self
                if name in init_hints:
                    param_type = python_type_to_ts(init_hints[name])
                    if param.default is inspect.Parameter.empty:
                        # Required parameter
                        init_params.append(name)
                        constructor_params.append(f"{name}: {param_type}")
                        constructor_assignments.append(f"    this.{name} = {name};")
                    else:
                        # Optional parameter
                        constructor_params.append(f"{name}?: {param_type}")
                        constructor_assignments.append(f"    if ({name} !== undefined) this.{name} = {name};")

                    # Add to attrs to ensure properties are created
                    attrs[name] = init_hints[name]

        except (TypeError, NameError):
            pass

    # Add property declarations with default values or definite assignment assertion
    for attr_name, attr_type in attrs.items():
        if not attr_name.startswith('_'):  # Skip private attributes
            ts_type = python_type_to_ts(attr_type)

            # Provide default initialization values based on type
            default_value = None
            if ts_type == "string":
                default_value = '""'  # Empty string
            elif ts_type == "number":
                default_value = "0"
            elif ts_type == "boolean":
                default_value = "false"
            elif ts_type.endswith("[]"):
                default_value = "[]"  # Empty array
            elif ts_type == "Date":
                default_value = "new Date()"
            elif "Record<" in ts_type or ts_type == "object":
                default_value = "{}"
            elif "Map<" in ts_type:
                default_value = "new Map()"
            elif "Set<" in ts_type:
                default_value = "new Set()"

            # Add the property declaration with initialization or definite assignment
            # For constructor parameters, we don't add default values
            if attr_name in init_params:
                # Use definite assignment assertion for required constructor params
                lines.append(f"  {attr_name}!: {ts_type};")
            elif default_value:
                lines.append(f"  {attr_name}: {ts_type} = {default_value};")
            else:
                # Use definite assignment assertion (!) for complex types without a clear default
                lines.append(f"  {attr_name}!: {ts_type};")  # The ! tells TypeScript this will be initialized

    # Add constructor with explicit required parameters
    if constructor_params:
        # Add specific constructor with required params
        lines.append(f"  constructor({', '.join(constructor_params)}, additionalArgs: Partial<{class_name}> = {{}}) {{")
        # Add explicit assignments for constructor parameters
        lines.extend(constructor_assignments)
        # Then apply any additional properties
        lines.append("    Object.assign(this, additionalArgs);")
        lines.append("  }")
    else:
        # Simple constructor with just args
        lines.append(f"  constructor(args: Partial<{class_name}> = {{}}) {{")
        lines.append("    Object.assign(this, args);")
        lines.append("  }")

    lines.append("")

    # Add methods
    for name, method in inspect.getmembers(cls, inspect.isfunction):
        if name.startswith('_'):
            continue  # Skip private/special methods except __init__

        # Include all methods in the class implementation
        try:
            method_hints = get_type_hints(method)
            params = list(inspect.signature(method).parameters.items())

            if params and params[0][0] == 'self':
                params = params[1:]  # Remove 'self' parameter

            # Separate required and optional parameters
            required_params = []
            optional_params = []
            required_param_names = []
            optional_param_names = []

            for param_name, param in params:
                if param_name in method_hints:
                    param_type = python_type_to_ts(method_hints[param_name])
                else:
                    param_type = "any"

                if param.default is inspect.Parameter.empty:
                    required_params.append(f"{param_name}: {param_type}")
                    required_param_names.append(param_name)
                else:
                    optional_params.append(f"{param_name}?: {param_type}")
                    optional_param_names.append(param_name)

            # Combine parameters with required first, then optional
            param_strings = required_params + optional_params
            param_names = required_param_names + optional_param_names

            return_type = "any"
            if "return" in method_hints and method_hints["return"] is not type(None):
                return_type = python_type_to_ts(method_hints["return"])

            # If class is decorated or method is decorated, all instance methods should call the backend
            # Only exclude static methods or other special cases
            if is_class_decorated or getattr(method, '_pyflow_decorated', False):
                lines.append(f"  async {name}({', '.join(param_strings)}): Promise<{return_type}> {{")
                # Get constructor parameters for method calls (important for classes with required params)
                constructor_args = []
                for param in init_params:
                    constructor_args.append(f"{param}: this.{param}")

                # Create arguments object
                if param_names:
                    args_obj = "{" + ', '.join(f'{pname}: {pname}' for pname in param_names) + "}"
                else:
                    args_obj = "{}"

                lines.append(f"    const result = await pyflowRuntime.callMethod(")
                lines.append(f"      '{class_name}',")
                lines.append(f"      '{name}',")
                lines.append(f"      {args_obj},")  # Regular method arguments
                lines.append(f"      {{{', '.join(constructor_args)}}},")  # Constructor args
                lines.append(f"      this")  # Pass this reference separately
                lines.append(f"    );")

                # Store instance ID if it was returned - with proper null check
                lines.append(f"    if (result && result.__instance_id__) {{")
                lines.append(f"      this._instanceId = result.__instance_id__;")
                lines.append(f"      if (this._instanceId) {{")  # Add null check
                lines.append(f"        pyflowRuntime.registerInstance(this, this._instanceId);")
                lines.append(f"      }}")
                lines.append(f"      delete result.__instance_id__;")
                lines.append(f"    }}")

                lines.append(f"    return result;")
                lines.append(f"  }}")
            else:
                # For non-decorated methods in non-decorated classes, provide a stub implementation
                lines.append(f"  {name}({', '.join(param_strings)}): {return_type} {{")
                if return_type != "void":
                    lines.append(f"    throw new Error('Method {name} not implemented');")
                lines.append(f"  }}")

            lines.append("")

        except (TypeError, ValueError):
            # Skip methods with invalid signatures
            pass

    # Add createInstance static method with improved instance tracking
    if constructor_params:
        # For classes with required constructor params
        req_params = []
        opt_params = []
        for param in constructor_params:
            if '?' in param:
                opt_params.append(param)
            else:
                req_params.append(param)

        params_list = req_params + opt_params

        lines.append(f"  static async createInstance({', '.join(params_list)}, additionalArgs: Partial<{class_name}> = {{}}): Promise<{class_name}> {{")
        lines.append(f"    const constructorArgs = {{{', '.join([p.split(':')[0].replace('?', '') for p in constructor_params])}}};")
        lines.append(f"    const instance = new {class_name}({', '.join([p.split(':')[0].replace('?', '') for p in params_list])}, additionalArgs);")
        lines.append(f"    const instanceId = await pyflowRuntime.createInstance('{class_name}', constructorArgs);")
        lines.append(f"    instance._instanceId = instanceId;")
        lines.append(f"    if (instanceId) {{")  # Add null check
        lines.append(f"      pyflowRuntime.registerInstance(instance, instanceId);")
        lines.append(f"    }}")
        lines.append("    return instance;")
        lines.append("  }")
    else:
        # Simple case - no required params
        lines.append(f"  static async createInstance(args: Partial<{class_name}> = {{}}): Promise<{class_name}> {{")
        lines.append(f"    const instance = new {class_name}(args);")
        lines.append(f"    const instanceId = await pyflowRuntime.createInstance('{class_name}', args);")
        lines.append(f"    instance._instanceId = instanceId;")
        lines.append(f"    if (instanceId) {{")  # Add null check
        lines.append(f"      pyflowRuntime.registerInstance(instance, instanceId);")
        lines.append(f"    }}")
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

    if func_name.startswith('_'):
        return ""  # Skip private functions

    try:
        hints = get_type_hints(func)
        params = list(inspect.signature(func).parameters.items())

        # Separate required and optional parameters
        required_params = []
        optional_params = []
        required_param_names = []
        optional_param_names = []

        for param_name, param in params:
            if param_name in hints:
                param_type = python_type_to_ts(hints[param_name])
            else:
                param_type = "any"

            if param.default is inspect.Parameter.empty:
                required_params.append(f"{param_name}: {param_type}")
                required_param_names.append(param_name)
            else:
                optional_params.append(f"{param_name}?: {param_type}")
                optional_param_names.append(param_name)

        # Combine parameters with required first, then optional
        param_strings = required_params + optional_params
        param_names = required_param_names + optional_param_names

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
    class_name = cls.__name__

    # Generate a class without interface/implementation split
    class_code = f"""
export class {class_name} {{
"""

    # Add property declarations with default values
    try:
        attrs = get_type_hints(cls)
    except (TypeError, NameError):
        attrs = {}

    # Extract initialization parameters from __init__
    init_params = []
    constructor_params = []
    param_types = {}

    # Track if we've seen an optional parameter already
    has_optional_param = False

    if hasattr(cls, "__init__") and cls.__init__ is not object.__init__:
        try:
            init_sig = inspect.signature(cls.__init__)
            init_hints = get_type_hints(cls.__init__)

            # Skip 'self' parameter
            for name, param in list(init_sig.parameters.items())[1:]:
                param_type = "any"
                if name in init_hints:
                    param_type = python_type_to_ts(init_hints[name])

                param_types[name] = param_type

                # Determine if this parameter is optional or needs a default value
                is_optional = param.default is not inspect.Parameter.empty
                if is_optional:
                    has_optional_param = True
                    constructor_params.append(f"{name}?: {param_type}")
                elif has_optional_param:
                    # If we've already seen an optional parameter, all subsequent params need defaults
                    # Determine appropriate default value by name convention
                    default_value = "{}"
                    if name == "args" or name.endswith("_args"):
                        default_value = "[]"
                    elif name == "kwargs" or name.endswith("_kwargs") or "kwargs" in name:
                        default_value = "{}"

                    constructor_params.append(f"{name}: {param_type} = {default_value}")
                else:
                    constructor_params.append(f"{name}: {param_type}")

                init_params.append(name)

                # Ensure all constructor parameters are added as class properties
                if name not in attrs:
                    attrs[name] = init_hints.get(name, Any)
        except (TypeError, NameError):
            pass

    # Add property declarations for all properties
    for attr_name, attr_type in attrs.items():
        if not attr_name.startswith('_'):  # Skip private attributes
            ts_type = python_type_to_ts(attr_type)

            # Provide default values based on type
            default_value = None
            if ts_type == "string":
                default_value = '""'  # Empty string
            elif ts_type == "number":
                default_value = "0"
            elif ts_type == "boolean":
                default_value = "false"
            elif ts_type.endswith("[]"):
                default_value = "[]"  # Empty array
            elif ts_type == "Date":
                default_value = "new Date()"
            elif "Record<" in ts_type or ts_type == "object":
                default_value = "{}"
            elif "Map<" in ts_type:
                default_value = "new Map()"
            elif "Set<" in ts_type:
                default_value = "new Set()"

            if attr_name in init_params:
                # Use the correct type for constructor parameters
                ts_type = param_types.get(attr_name, ts_type)
                # For constructor params, don't provide a default value in the declaration
                # but use the definite assignment assertion
                class_code += f"  {attr_name}?: {ts_type};\n"
            elif default_value:
                class_code += f"  {attr_name}: {ts_type} = {default_value};\n"
            else:
                # Use definite assignment assertion (!) for complex types without a clear default
                class_code += f"  {attr_name}!: {ts_type};\n"

    # Add constructor with actual init parameters
    if constructor_params:
        # Make all parameters after first required one optional to make TypeScript happy
        class_code += f"""
  constructor({', '.join(constructor_params)}) {{
    // Initialize properties
"""
        # Add assignments for each parameter
        for param in init_params:
            # Only set the property if the parameter was provided
            class_code += f"    if ({param} !== undefined) this.{param} = {param};\n"

        # End constructor
        class_code += "  }\n"
    else:
        class_code += f"""
  constructor(data: Record<string, any> = {{}}) {{
    Object.assign(this, data);
  }}
"""

    class_code += "}\n"

    # Add factory function that accepts an options object
    class_code += f"""
export function create{class_name}(options: Partial<{class_name}> = {{}}): {class_name} {{
  return new {class_name}(options as any);
}}
"""

    return class_code
