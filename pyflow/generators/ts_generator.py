"""
TypeScript code generator for PyFlow.ts.
"""
from pathlib import Path
import inspect
import importlib
from typing import get_type_hints, List, Dict, Any, Type

from ..core import registry
from ..utils.type_converter import (
    generate_ts_interface,
    generate_ts_class,
    generate_ts_function,
    generate_ts_type
)
from ..utils.inspect_utils import get_all_referenced_types

class TypeScriptGenerator:
    """Generate TypeScript code from registered Python objects."""

    def __init__(self, output_dir: Path, host: str = "localhost", port: int = 8000, debug: bool = False):
        self.output_dir = output_dir
        self.host = host
        self.port = port
        self.runtime_code = f"""// PyFlow.ts runtime for TypeScript
export interface PyFlowRuntime {{
  callFunction(moduleName: string, functionName: string, args: any): any;
  callMethod(className: string, methodName: string, args: any, constructorArgs: any): any;
  createInstance(className: string, constructorArgs: any): any;
}}

// Default implementation that uses fetch to call the Python API
class DefaultPyFlowRuntime implements PyFlowRuntime {{
  apiUrl: string;
  debug: boolean;

  // Track instances by ID
  private instanceCache = new Map<string, string>();

  debugLog(message: string, data?: any) {{
    if (this.debug) {{
      if (data) {{
        console.log(`[pyflow] ${{message}}`, data);
      }} else {{
        console.log(`[pyflow] ${{message}}`);
      }}
    }}
  }}

  constructor(apiUrl: string = 'http://{self.host}:{self.port}/api', debug: boolean = {str(debug).lower()}) {{
    this.apiUrl = apiUrl;
    this.debug = debug;
    this.debugLog(`Initialized with API URL: ${{this.apiUrl}}`);
  }}

  async callFunction(moduleName: string, functionName: string, args: any): Promise<any> {{
    this.debugLog(`Calling function: ${{moduleName}}.${{functionName}}`, {{
      module: moduleName,
      function: functionName,
      args: args
    }});

    const response = await fetch(`${{this.apiUrl}}/call-function`, {{
      method: 'POST',
      headers: {{
        'Content-Type': 'application/json',
      }},
      body: JSON.stringify({{
        module: moduleName,
        function: functionName,
        args: args,
      }}),
    }});

    if (!response.ok) {{
      const error = await response.text();
      this.debugLog(`Error calling function: ${{error}}`);
      throw new Error(`Failed to call Python function: ${{error}}`);
    }}

    const data = await response.json();
    this.debugLog(`Function result:`, data.result);
    return data.result;
  }}

  async createInstance(className: string, constructorArgs: any): Promise<string> {{
    this.debugLog(`Creating instance of: ${{className}}`, {{
      class: className,
      constructorArgs: constructorArgs
    }});

    const response = await fetch(`${{this.apiUrl}}/create-instance`, {{
      method: 'POST',
      headers: {{
        'Content-Type': 'application/json',
      }},
      body: JSON.stringify({{
        class: className,
        constructor_args: constructorArgs,
      }}),
    }});

    if (!response.ok) {{
      const error = await response.text();
      this.debugLog(`Error creating instance: ${{error}}`);
      throw new Error(`Failed to create instance: ${{error}}`);
    }}

    const data = await response.json();
    this.instanceCache.set(className, data.instance_id);
    this.debugLog(`Created instance with ID: ${{data.instance_id}}`);
    return data.instance_id;
  }}

  async callMethod(className: string, methodName: string, args: any, constructorArgs: any): Promise<any> {{
    const instanceId = this.instanceCache.get(className);
    this.debugLog(`Calling method: ${{className}}.${{methodName}}`, {{
      class: className,
      method: methodName,
      args: args,
      constructorArgs: constructorArgs,
      instanceId: instanceId
    }});

    const response = await fetch(`${{this.apiUrl}}/call-method`, {{
      method: 'POST',
      headers: {{
        'Content-Type': 'application/json',
      }},
      body: JSON.stringify({{
        class: className,
        method: methodName,
        args: args,
        constructor_args: constructorArgs,
        instance_id: instanceId,
      }}),
    }});

    if (!response.ok) {{
      const error = await response.text();
      this.debugLog(`Error calling method: ${{error}}`);
      throw new Error(`Failed to call Python method: ${{error}}`);
    }}

    const data = await response.json();
    this.debugLog(`Method result:`, data.result);
    return data.result;
  }}
}}

// Export a global instance
export const pyflowRuntime: PyFlowRuntime = new DefaultPyFlowRuntime();
"""

    def generate_runtime(self) -> None:
        """Generate the PyFlow.ts runtime TypeScript file."""
        runtime_path = self.output_dir / "pyflowRuntime.ts"

        with open(runtime_path, 'w') as f:
            f.write(self.runtime_code)

        print(f"Generated PyFlow.ts runtime at {runtime_path}")

    def _get_classes_with_decorated_methods(self, module_name: str) -> List[Type]:
        """Identify classes that have PyFlow.ts-decorated methods but aren't decorated themselves."""
        try:
            module = importlib.import_module(module_name)
            result = []

            # Keep track of class-method registrations
            class_methods = {}

            # First, identify classes from functions that look like methods (have 'self' parameter)
            for func_name, func_info in registry.functions.items():
                if func_info['module'] != module_name:
                    continue

                func = func_info['func']
                signature = func_info.get('signature', None)

                # If we can't get the signature directly, get it from the function
                if signature is None:
                    signature = inspect.signature(func)

                params = list(signature.parameters.keys())

                # If it has 'self' as first parameter, it's likely a method
                if params and params[0] == 'self':
                    # Try to find the class this method belongs to
                    for name, obj in inspect.getmembers(module):
                        if inspect.isclass(obj) and obj.__module__ == module_name:
                            if hasattr(obj, func.__name__):
                                class_method = f"{obj.__name__}"

                                if class_method not in class_methods:
                                    class_methods[class_method] = []

                                class_methods[class_method].append(func.__name__)
                                break

            # Now go through registry.classes and extract class methods
            for class_name, class_info in registry.classes.items():
                if class_info['module'] != module_name:
                    continue

                # Get the class from the module
                cls = class_info.get('cls', None)
                if not cls:
                    continue

                # Look for methods specifically registered for this class
                for method_name in class_info.get('methods', {}):
                    # Skip __init__ and other dunder methods
                    if method_name == '__init__' or (method_name.startswith('__') and method_name.endswith('__')):
                        continue

                    # For this class, find all other classes that have this method decorated
                    for name, obj in inspect.getmembers(module):
                        if inspect.isclass(obj) and obj.__module__ == module_name and obj is not cls:
                            # If the class has the method and it's not already in our results
                            if hasattr(obj, method_name) and obj not in result:
                                result.append(obj)
                                break

            # Add classes found from the class_methods dictionary
            for class_name, methods in class_methods.items():
                if methods:  # If the class has any decorated methods
                    # Find the class in the module
                    for name, obj in inspect.getmembers(module):
                        if inspect.isclass(obj) and obj.__module__ == module_name and obj.__name__ == class_name:
                            if obj not in result:
                                result.append(obj)
                                break

            return result
        except ImportError:
            print(f"Warning: Could not import module {module_name}")
            return []

    def generate_module(self, module_name: str) -> None:
        """Generate TypeScript code for a Python module."""
        # Create output directory if it doesn't exist
        module_path = module_name.replace('.', '/')
        output_dir = self.output_dir / module_path
        output_dir.mkdir(parents=True, exist_ok=True)

        # Find all PyFlow.ts-decorated objects in this module
        module_classes = []
        module_functions = []
        module_referenced_classes = []
        classes_with_decorated_methods = []

        # Track classes we've processed to avoid duplicates
        processed_classes = set()

        # Get decorated classes
        for class_name, class_info in registry.classes.items():
            if class_info['module'] == module_name:
                cls = class_info['cls']
                module_classes.append(cls)
                processed_classes.add(cls.__name__)

        # Find classes with decorated methods but not yet processed
        classes_with_decorated_methods = self._get_classes_with_decorated_methods(module_name)
        # Filter out classes already processed
        classes_with_decorated_methods = [cls for cls in classes_with_decorated_methods
                                         if cls.__name__ not in processed_classes]

        # Add to processed set
        for cls in classes_with_decorated_methods:
            processed_classes.add(cls.__name__)

        # Get decorated functions
        for func_name, func_info in registry.functions.items():
            if func_info['module'] == module_name:
                module_functions.append(func_info['func'])

        # Find classes referenced in signatures but not decorated
        referenced_types = get_all_referenced_types(module_name)

        # Add parent classes of decorated classes that aren't themselves decorated
        for cls in module_classes:
            class_name = cls.__name__
            # Find parent classes to add
            for name, obj in inspect.getmembers(inspect.getmodule(cls)):
                if inspect.isclass(obj) and obj.__module__ == module_name:
                    # Check if this class is a parent of any decorated class
                    if issubclass(cls, obj) and obj is not cls and obj not in module_classes:
                        referenced_types[obj.__name__] = obj

                    # Check if class is used in any method signature
                    for decorated_cls in module_classes:
                        for method_name, method in inspect.getmembers(decorated_cls, inspect.isfunction):
                            if not method_name.startswith('_') or method_name == '__init__':
                                hints = get_type_hints(method)
                                for type_hint in hints.values():
                                    if type_hint is obj or (getattr(type_hint, '__origin__', None) and type_hint.__args__ and type_hint.__args__[0] is obj):
                                        referenced_types[obj.__name__] = obj

        # Remove classes that are already decorated
        for cls in module_classes:
            if cls.__name__ in referenced_types:
                del referenced_types[cls.__name__]

        # Remove classes that are already in classes_with_decorated_methods
        for cls in classes_with_decorated_methods:
            if cls.__name__ in referenced_types:
                del referenced_types[cls.__name__]

        # Convert dict to list
        module_referenced_classes = list(referenced_types.values())

        # Remove classes that are already in processed_classes
        module_referenced_classes = [cls for cls in module_referenced_classes
                                   if cls.__name__ not in processed_classes]

        if not module_classes and not module_functions and not module_referenced_classes and not classes_with_decorated_methods:
            print(f"No PyFlow.ts-decorated objects found in module {module_name}")
            return

        # Calculate how many levels deep we are to create the correct relative path
        depth = len(module_name.split('.'))
        import_path = '../' * depth

        # Generate TypeScript code with correct import path
        ts_code = f"""// Generated by PyFlow.ts - DO NOT EDIT
import {{ pyflowRuntime }} from '{import_path}pyflowRuntime.js';

"""

        # Generate interfaces for referenced classes
        for cls in module_referenced_classes:
            ts_code += generate_ts_type(cls) + "\n\n"
            processed_classes.add(cls.__name__)

        # Generate interfaces and classes for decorated classes
        for cls in module_classes:
            ts_code += generate_ts_interface(cls) + "\n\n"
            ts_code += generate_ts_class(cls) + "\n\n"

        # Generate interfaces and classes for classes with decorated methods
        for cls in classes_with_decorated_methods:
            ts_code += generate_ts_interface(cls) + "\n\n"
            ts_code += generate_ts_class(cls) + "\n\n"

        # Generate functions
        for func in module_functions:
            ts_code += generate_ts_function(func) + "\n\n"

        # Write to file
        output_file = output_dir / "index.ts"
        with open(output_file, 'w') as f:
            f.write(ts_code)

        print(f"Generated TypeScript code for module {module_name} at {output_file}")

        # Copy runtime file to each module's level for proper imports
        # Determine the parent directory where pyflowRuntime should be
        parent_dir = output_dir
        for _ in range(depth - 1):
            parent_dir = parent_dir.parent

        # Copy the runtime file to this level if it doesn't exist
        target_runtime_path = parent_dir / "pyflowRuntime.ts"
        if not target_runtime_path.exists():
            # Make sure parent directory exists
            parent_dir.mkdir(parents=True, exist_ok=True)

            # Write the runtime code to this location
            with open(target_runtime_path, 'w') as f:
                f.write(self.runtime_code)
            print(f"Generated runtime at {target_runtime_path}")

    def generate_index(self) -> None:
        """Generate index.ts files for exporting."""
        for module_name in registry.modules:
            module_parts = module_name.split('.')

            # Generate index files for each level
            for i in range(1, len(module_parts) + 1):
                parent_module = '.'.join(module_parts[:i])
                parent_path = self.output_dir / parent_module.replace('.', '/')

                if i < len(module_parts):
                    # This is a parent module, export all its children
                    child_name = module_parts[i]
                    index_file = parent_path / "index.ts"
                    export_line = f"export * from './{child_name}/index.js';\n"

                    if index_file.exists():
                        with open(index_file, 'r') as f:
                            content = f.read()
                            if export_line not in content:
                                with open(index_file, 'a') as f:
                                    f.write(export_line)
                    else:
                        parent_path.mkdir(parents=True, exist_ok=True)
                        with open(index_file, 'w') as f:
                            f.write(export_line)

    def generate_all(self) -> None:
        """Generate TypeScript code for all registered modules."""
        # First generate the runtime in the root directory
        self.generate_runtime()

        # Then generate modules (which will also copy runtime to appropriate locations)
        for module_name in registry.modules:
            self.generate_module(module_name)

        # Finally generate index files
        self.generate_index()