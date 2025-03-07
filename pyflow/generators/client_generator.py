"""
Client code generator for PyFlow.ts.
"""
from pathlib import Path

class ClientGenerator:
    """Generate client code for accessing the PyFlow.ts API."""

    def __init__(self, output_dir: Path, host: str = "localhost", port: int = 8000, debug: bool = True):
        self.output_dir = output_dir
        self.host = host
        self.port = port
        self.api_url = f"http://{host}:{port}/api"
        self.debug = debug

    def generate_python_client(self) -> None:
        """Generate a Python client for the PyFlow.ts API."""
        client_code = f'''# Generated by PyFlow.ts - DO NOT EDIT
import requests
import json
from typing import Any, Dict, List, Optional, Union

class PyFlowClient:
    """Client for calling PyFlow.ts-decorated functions and methods."""

    def __init__(self, api_url: str = "{self.api_url}", debug: bool = {str(self.debug)}):
        self.api_url = api_url
        self.instance_cache = {{}}  # Store instances by class name
        self.debug = debug

    def _log(self, message: str) -> None:
        """Print debug message if debug mode is enabled."""
        if self.debug:
            print(f"[PyFlowClient] {{message}}")

    def call_function(self, module: str, function: str, args: Dict[str, Any]) -> Any:
        """Call a Python function through the PyFlow.ts API."""
        self._log(f"Calling function: {{module}}.{{function}}()")
        self._log(f"Arguments: {{json.dumps(args, default=str)}}")

        try:
            response = requests.post(
                f"{{self.api_url}}/call-function",
                json={{
                    "module": module,
                    "function": function,
                    "args": args
                }}
            )

            if response.status_code != 200:
                self._log(f"API call failed with status: {{response.status_code}}")
                self._log(f"Response: {{response.text}}")
                raise Exception(f"API call failed: {{response.text}}")

            result = response.json()["result"]
            self._log(f"Function call successful. Result type: {{type(result).__name__}}")
            return result

        except Exception as e:
            self._log(f"Error in call_function: {{str(e)}}")
            raise

    def create_instance(self, class_name: str, constructor_args: Dict[str, Any] = None) -> str:
        """Create an instance of a class and return its ID."""
        constructor_args = constructor_args or {{}}
        self._log(f"Creating instance of class: {{class_name}}")
        self._log(f"Constructor arguments: {{json.dumps(constructor_args, default=str)}}")

        try:
            payload = {{
                "class": class_name,
                "constructor_args": constructor_args or {{}}
            }}

            response = requests.post(
                f"{{self.api_url}}/create-instance",
                json=payload
            )

            if response.status_code != 200:
                self._log(f"Instance creation failed with status: {{response.status_code}}")
                self._log(f"Response: {{response.text}}")
                raise Exception(f"API call failed: {{response.text}}")

            result = response.json()
            instance_id = result["instance_id"]
            self.instance_cache[class_name] = instance_id
            self._log(f"Instance created successfully with ID: {{instance_id}}")
            return instance_id

        except Exception as e:
            self._log(f"Error in create_instance: {{str(e)}}")
            raise

    def call_method(self, class_name: str, method_name: str, args: Dict[str, Any],
                   constructor_args: Dict[str, Any] = None, instance_id: str = None) -> Any:
        """Call a method on a Python class through the PyFlow.ts API."""
        self._log(f"Calling method: {{class_name}}.{{method_name}}()")
        self._log(f"Arguments: {{json.dumps(args, default=str)}}")

        # Use cached instance ID if available and none was provided
        if instance_id is None:
            instance_id = self.instance_cache.get(class_name)
            if instance_id:
                self._log(f"Using cached instance ID: {{instance_id}}")
            else:
                self._log(f"No instance ID found, will create new instance")

        try:
            payload = {{
                "class": class_name,
                "method": method_name,
                "args": args
            }}

            if constructor_args is not None:
                payload["constructor_args"] = constructor_args
                self._log(f"Using constructor args: {{json.dumps(constructor_args, default=str)}}")

            if instance_id is not None:
                payload["instance_id"] = instance_id

            response = requests.post(
                f"{{self.api_url}}/call-method",
                json=payload
            )

            if response.status_code != 200:
                self._log(f"Method call failed with status: {{response.status_code}}")
                self._log(f"Response: {{response.text}}")
                raise Exception(f"API call failed: {{response.text}}")

            result = response.json()["result"]
            self._log(f"Method call successful. Result type: {{type(result).__name__}}")
            return result

        except Exception as e:
            self._log(f"Error in call_method: {{str(e)}}")
            raise
'''

        # Create the output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Write the client file
        client_file = self.output_dir / "client.py"
        with open(client_file, 'w') as f:
            f.write(client_code)

        print(f"Generated Python client at {client_file}")

    def generate_js_client(self) -> None:
        """Generate a JavaScript client for the PyFlow.ts API."""
        client_code = f'''// Generated by PyFlow.ts - DO NOT EDIT

export class PyFlowClient {{
  /**
   * Client for calling PyFlow.ts-decorated functions and methods.
   */
  constructor(apiUrl = "{self.api_url}", debug = {str(self.debug).lower()}) {{
    this.apiUrl = apiUrl;
    this.instanceCache = new Map(); // Store instance IDs by class name
    this.debug = debug;
  }}

  _log(message) {{
    if (this.debug) {{
      console.log(`[PyFlowClient] ${{message}}`);
    }}
  }}

  async callFunction(module, functionName, args) {{
    /**
     * Call a Python function through the PyFlow.ts API.
     */
    this._log(`Calling function: ${{module}}.${{functionName}}()`);
    this._log(`Arguments: ${{JSON.stringify(args, null, 2)}}`);

    try {{
      const response = await fetch(`${{this.apiUrl}}/call-function`, {{
        method: 'POST',
        headers: {{
          'Content-Type': 'application/json',
        }},
        body: JSON.stringify({{
          module: module,
          function: functionName,
          args: args,
        }}),
      }});

      if (!response.ok) {{
        const errorText = await response.text();
        this._log(`API call failed with status: ${{response.status}}`);
        this._log(`Response: ${{errorText}}`);
        throw new Error(`API call failed: ${{errorText}}`);
      }}

      const data = await response.json();
      this._log(`Function call successful. Result: ${{typeof data.result}}`);
      return data.result;
    }} catch (error) {{
      this._log(`Error in callFunction: ${{error.message}}`);
      throw error;
    }}
  }}

  async createInstance(className, constructorArgs = {{}}) {{
    /**
     * Create an instance of a class and return its ID.
     */
    this._log(`Creating instance of class: ${{className}}`);
    this._log(`Constructor arguments: ${{JSON.stringify(constructorArgs, null, 2)}}`);

    try {{
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
        const errorText = await response.text();
        this._log(`Instance creation failed with status: ${{response.status}}`);
        this._log(`Response: ${{errorText}}`);
        throw new Error(`API call failed: ${{errorText}}`);
      }}

      const data = await response.json();
      this.instanceCache.set(className, data.instance_id);
      this._log(`Instance created successfully with ID: ${{data.instance_id}}`);
      return data.instance_id;
    }} catch (error) {{
      this._log(`Error in createInstance: ${{error.message}}`);
      throw error;
    }}
  }}

  async callMethod(className, methodName, args, constructorArgs = {{}}, instanceId = null) {{
    /**
     * Call a method on a Python class through the PyFlow.ts API.
     */
    this._log(`Calling method: ${{className}}.${{methodName}}()`);
    this._log(`Arguments: ${{JSON.stringify(args, null, 2)}}`);

    // Use cached instance ID if available and none was provided
    if (instanceId === null) {{
      instanceId = this.instanceCache.get(className);
      if (instanceId) {{
        this._log(`Using cached instance ID: ${{instanceId}}`);
      }} else {{
        this._log(`No instance ID found, will create new instance`);
      }}
    }}

    try {{
      const payload = {{
        class: className,
        method: methodName,
        args: args,
      }};

      if (Object.keys(constructorArgs).length > 0) {{
        payload.constructor_args = constructorArgs;
        this._log(`Using constructor args: ${{JSON.stringify(constructorArgs, null, 2)}}`);
      }}

      if (instanceId) {{
        payload.instance_id = instanceId;
      }}

      const response = await fetch(`${{this.apiUrl}}/call-method`, {{
        method: 'POST',
        headers: {{
          'Content-Type': 'application/json',
        }},
        body: JSON.stringify(payload),
      }});

      if (!response.ok) {{
        const errorText = await response.text();
        this._log(`Method call failed with status: ${{response.status}}`);
        this._log(`Response: ${{errorText}}`);
        throw new Error(`API call failed: ${{errorText}}`);
      }}

      const data = await response.json();
      this._log(`Method call successful. Result: ${{typeof data.result}}`);
      return data.result;
    }} catch (error) {{
      this._log(`Error in callMethod: ${{error.message}}`);
      throw error;
    }}
  }}
}}
'''

        # Create the output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Write the client file
        client_file = self.output_dir / "client.js"
        with open(client_file, 'w') as f:
            f.write(client_code)

        print(f"Generated JavaScript client at {client_file}")

    def generate_all(self) -> None:
        """Generate all client code."""
        self.generate_python_client()
        self.generate_js_client()
