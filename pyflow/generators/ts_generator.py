"""
TypeScript code generator for PyFlow.ts.
"""
from pathlib import Path
import inspect
import importlib
from typing import List, Type, Set

from ..core import registry
from ..utils.type_converter import (
    generate_ts_interface,
    generate_ts_class,
    generate_ts_function,
    generate_ts_type
)
from ..utils.inspect_utils import (
    get_all_referenced_types,
    get_decorated_items_in_module
)

class TypeScriptGenerator:
    """Generate TypeScript code from registered Python objects."""

    def __init__(self, output_dir: Path, host: str = "localhost", port: int = 8000, debug: bool = False):
        self.output_dir = output_dir
        self.host = host
        self.port = port
        self.debug = debug
        # Runtime code remains unchanged
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

    def _get_classes_with_decorated_methods(self, module_name: str, already_decorated_classes: Set[Type] = None) -> List[Type]:
        """
        Identify classes that have PyFlow.ts-decorated methods but aren't decorated themselves.
        Enhanced to better detect decorated methods and their containing classes.

        Args:
            module_name: The module to inspect
            already_decorated_classes: Set of classes to exclude (already directly decorated)
        """
        try:
            module = importlib.import_module(module_name)
            result = []

            # Setup set of already decorated classes (to exclude)
            if already_decorated_classes is None:
                already_decorated_classes = set()

            already_decorated_class_names = {cls.__name__ for cls in already_decorated_classes}

            # Track which classes have decorated methods
            classes_with_decorated_methods = set()

            # First check all classes in the module for decorated methods
            for name, cls in inspect.getmembers(module, inspect.isclass):
                if cls.__module__ != module_name:
                    continue

                # Skip if the class itself is decorated
                if getattr(cls, '_pyflow_decorated', False) or cls in already_decorated_classes or cls.__name__ in already_decorated_class_names:
                    continue

                # Check if any methods are decorated
                for method_name, method in inspect.getmembers(cls, inspect.isfunction):
                    if getattr(method, '_pyflow_decorated', False):
                        classes_with_decorated_methods.add(cls)
                        break

            # Now check if any function in the registry looks like a method
            for func_name, func_info in registry.functions.items():
                if func_info['module'] != module_name:
                    continue

                func = func_info['func']
                signature = func_info.get('signature', None) or inspect.signature(func)
                params = list(signature.parameters.keys())

                # If it has 'self' as first parameter, it's likely a method
                if params and params[0] == 'self':
                    # Try to find the class this method belongs to
                    for name, cls in inspect.getmembers(module, inspect.isclass):
                        if cls.__module__ == module_name and hasattr(cls, func.__name__):
                            method = getattr(cls, func.__name__)
                            if method.__code__ is func.__code__:
                                # Only add if not already directly decorated
                                if (not getattr(cls, '_pyflow_decorated', False) and
                                    cls not in already_decorated_classes and
                                    cls.__name__ not in already_decorated_class_names):
                                    classes_with_decorated_methods.add(cls)
                                    break

            # Add classes from registry that have decorated methods
            for class_name, class_info in registry.classes.items():
                if class_info['module'] == module_name:
                    cls = class_info.get('cls', None)
                    if cls and not getattr(cls, '_pyflow_decorated', False) and cls not in already_decorated_classes:
                        # Check if this class has any decorated methods
                        for method_name, method_info in class_info.get('methods', {}).items():
                            if method_info.get('method') and getattr(method_info.get('method'), '_pyflow_decorated', False):
                                classes_with_decorated_methods.add(cls)
                                break

            # Convert the set to a list
            result = list(classes_with_decorated_methods)
            return result

        except ImportError:
            print(f"Warning: Could not import module {module_name}")
            return []

    def _get_decorated_class_tree(self, cls: Type, processed_classes: Set[str]) -> List[Type]:
        """Get all parent classes of a decorated class that should be included."""
        result = []

        # Skip processing if already processed or if class is None
        if not cls or cls.__name__ in processed_classes:
            return result

        # Track the base classes we want to include
        for base in cls.__bases__:
            # Always include important base classes in the hierarchy
            if base.__name__ != "object" and base.__module__ != "builtins":
                if base.__name__ not in processed_classes:
                    result.append(base)
                    processed_classes.add(base.__name__)

                    # Recursively process the base class's parents
                    result.extend(self._get_decorated_class_tree(base, processed_classes))

        return result

    def generate_module(self, module_name: str) -> None:
        """Generate TypeScript code for a Python module."""
        # Create output directory if it doesn't exist
        module_path = module_name.replace('.', '/')
        output_dir = self.output_dir / module_path
        output_dir.mkdir(parents=True, exist_ok=True)

        print(f"Processing module: {module_name}")

        # Check if this is a known web framework module
        is_web_framework = any(framework in module_name.lower() for framework in ["flask", "django", "fastapi", "web"])

        try:
            # Get decorated classes and functions directly
            decorated_classes, decorated_functions = [], []
            try:
                decorated_classes, decorated_functions = get_decorated_items_in_module(module_name)
            except RuntimeError as e:
                if "request context" in str(e).lower():
                    print(f"Web framework detected in {module_name}, using registry information only")
                    # For web frameworks, rely solely on registry information
                    is_web_framework = True
                else:
                    raise

            # Add decorated classes from registry
            for class_name, class_info in registry.classes.items():
                if class_info['module'] == module_name:
                    cls = class_info.get('cls')
                    if cls and cls not in decorated_classes:
                        decorated_classes.append(cls)
                        print(f"Added class from registry: {cls.__name__}")

            # Find classes with decorated methods - pass decorated_classes to exclude them
            classes_with_decorated_methods = []
            if not is_web_framework:  # Skip this for web framework modules
                try:
                    classes_with_decorated_methods = self._get_classes_with_decorated_methods(module_name, set(decorated_classes))
                except RuntimeError as e:
                    if "request context" in str(e).lower():
                        print(f"Skipping method detection for web framework module {module_name}")
                    else:
                        raise

            # Add decorated functions from registry
            for func_name, func_info in registry.functions.items():
                if func_info['module'] == module_name:
                    func = func_info.get('func')
                    if func and func not in decorated_functions:
                        decorated_functions.append(func)
                        print(f"Added function from registry: {func.__name__}")

            # Get all referenced types - this will include types from signatures and inheritance
            referenced_types = []
            try:
                all_referenced_types = get_all_referenced_types(module_name)

                # Exclude types that are already in our decorated lists
                processed_class_names = {cls.__name__ for cls in decorated_classes + classes_with_decorated_methods}

                for type_name, type_cls in all_referenced_types.items():
                    if (type_name not in processed_class_names and
                        not type_name.startswith('_') and
                        not (is_web_framework and hasattr(type_cls, 'route'))):  # Skip Flask route objects
                        referenced_types.append(type_cls)
                        processed_class_names.add(type_name)
            except RuntimeError as e:
                if "request context" in str(e).lower():
                    print(f"Skipping referenced type detection for web framework module {module_name}")
                else:
                    raise

            # If nothing to generate, return
            if not decorated_classes and not decorated_functions and not referenced_types and not classes_with_decorated_methods:
                print(f"No PyFlow.ts-decorated objects found in module {module_name}")
                return

            # Let's do a final check to make sure there's no overlap
            decorated_class_names = {cls.__name__ for cls in decorated_classes}
            classes_with_decorated_methods = [cls for cls in classes_with_decorated_methods
                                              if cls.__name__ not in decorated_class_names]

            # Log what we found
            print(f"Found in {module_name}:")
            print(f"  - {len(decorated_classes)} decorated classes")
            print(f"  - {len(decorated_functions)} decorated functions")
            print(f"  - {len(classes_with_decorated_methods)} classes with decorated methods")
            print(f"  - {len(referenced_types)} referenced types")

            # Calculate import path
            depth = len(module_name.split('.'))
            import_path = '../' * depth

            # Generate TypeScript code
            ts_code = f"""// Generated by PyFlow.ts - DO NOT EDIT
import {{ pyflowRuntime }} from '{import_path}pyflowRuntime.js';

"""
            # Track what we've already generated to avoid duplicates
            generated_types = set()

            # Generate interfaces for referenced types first
            for cls in referenced_types:
                try:
                    if cls.__name__ in generated_types:
                        continue  # Skip if already generated

                    type_code = generate_ts_type(cls)
                    if type_code.strip():  # Only add if there's actual content
                        ts_code += type_code + "\n\n"
                        generated_types.add(cls.__name__)
                    else:
                        print(f"Warning: Empty type generated for {cls.__name__}")
                except Exception as e:
                    print(f"Error generating type for {cls.__name__}: {str(e)}")

            # Generate interfaces and classes for decorated classes
            for cls in decorated_classes:
                try:
                    if cls.__name__ in generated_types:
                        continue  # Skip if already generated

                    class_code = generate_ts_class(cls)

                    if class_code.strip():
                        ts_code += class_code + "\n\n"
                    else:
                        print(f"Warning: Empty class generated for {cls.__name__}")
                except Exception as e:
                    print(f"Error generating interface/class for {cls.__name__}: {str(e)}")

            # Generate interfaces and classes for classes with decorated methods
            for cls in classes_with_decorated_methods:
                try:
                    if cls.__name__ in generated_types:
                        continue  # Skip if already generated

                    class_code = generate_ts_class(cls)

                    if class_code.strip():
                        ts_code += class_code + "\n\n"
                    else:
                        print(f"Warning: Empty class generated for method class {cls.__name__}")
                except Exception as e:
                    print(f"Error generating interface/class for method class {cls.__name__}: {str(e)}")

            # Generate functions
            for func in decorated_functions:
                try:
                    func_code = generate_ts_function(func)
                    if func_code.strip():
                        ts_code += func_code + "\n\n"
                    else:
                        print(f"Warning: Empty function generated for {func.__name__}")
                except Exception as e:
                    print(f"Error generating function for {func.__name__}: {str(e)}")

            # Write to file
            output_file = output_dir / "index.ts"
            with open(output_file, 'w') as f:
                f.write(ts_code)
                print(ts_code)
                print(output_file)

            print(f"Generated TypeScript code for module {module_name} at {output_file}")

            # Handle runtime file for proper imports
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
        except Exception as e:
            print(f"Error processing module {module_name}: {str(e)}")
            import traceback
            traceback.print_exc()
            print("Continuing with next module...")

    def generate_index(self) -> None:
        """Generate index.ts files for exporting."""
        # Build a module tree to determine the correct hierarchical structure
        module_tree = {}

        # First, identify all modules that have decorated items
        for module_name in registry.modules:
            parts = module_name.split('.')

            # Add each level to the tree
            for i in range(1, len(parts) + 1):
                parent = '.'.join(parts[:i])
                if parent not in module_tree:
                    module_tree[parent] = set()

                # Add child to parent if this isn't the end of the path
                if i < len(parts):
                    child = '.'.join(parts[:i+1])
                    module_tree[parent].add(child)

        # Generate index files for each module level
        for module_name, children in module_tree.items():
            module_path = self.output_dir / module_name.replace('.', '/')
            module_path.mkdir(parents=True, exist_ok=True)

            # Only create index files where needed
            if children or module_name in registry.modules:
                # Get direct children only
                direct_children = []
                for child in children:
                    child_parts = child.split('.')
                    if len(child_parts) == len(module_name.split('.')) + 1:
                        direct_children.append(child_parts[-1])

                # Create index file content
                index_path = module_path / 'index.ts'
                content = "// Generated by PyFlow.ts - DO NOT EDIT\n"

                # Add exports from direct child modules
                if direct_children:
                    for child in sorted(direct_children):
                        content += f"export * from './{child}/index.js';\n"
                elif module_name in registry.modules:
                    content += "// No child modules to export, but this module contains decorated items\n"
                    content += "// The contents are directly available from this module\n"
                else:
                    content += "// Empty module structure\n"

                # Write the file if content is different from existing
                if not index_path.exists():
                    with open(index_path, 'w') as f:
                        f.write(content)
                        print(f"Created index file at {index_path}")
                else:
                    with open(index_path, 'r') as f:
                        existing_content = f.read()
                    if existing_content != content:
                        with open(index_path, 'a') as f:
                            f.write(content)
                            print(f"Updated index file at {index_path}")

        # Generate root index file with correct export paths
        root_index = self.output_dir / "index.ts"
        with open(root_index, 'w') as f:
            f.write("// Root index file generated by PyFlow.ts\n")
            f.write("// This file aggregates all exports from all modules\n\n")
            f.write("import { pyflowRuntime } from './pyflowRuntime.js';\n\n")

            exported_modules = []
            for module in sorted([m for m in module_tree.keys() if '.' not in m]):
                export_line = f"export * from './{module}/index.js';"
                f.write(f"{export_line}\n")
                exported_modules.append(module)

            # Add export for pyflowRuntime
            f.write("\nexport { pyflowRuntime };\n")

            print(f"Generated root index file with {len(exported_modules)} module exports: {', '.join(exported_modules)}")

    def generate_all(self) -> None:
        """Generate TypeScript code for all registered modules."""
        # First generate the runtime in the root directory
        self.generate_runtime()

        # Then generate modules (which will also copy runtime to appropriate locations)
        for module_name in registry.modules:
            self.generate_module(module_name)

        # Finally generate index files
        self.generate_index()