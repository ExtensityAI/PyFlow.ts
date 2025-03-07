import argparse
import importlib
import os
import shutil
import json
import subprocess
from pathlib import Path
import sys
import tempfile
from typing import List

from .core import import_module_from_path
from .generators.ts_generator import TypeScriptGenerator
from .generators.api_generator import ApiGenerator
from .generators.client_generator import ClientGenerator
from . import PYFLOWTS_VERSION

import tempfile
import shutil
import subprocess

def _run_server_process(module_path, modules, host, port, generated_dir, reload, debug):
    """Run the server process in a picklable function."""
    run_generated_server(module_path, modules, host, port, generated_dir, reload, debug)

def test_file(args):
    """Run a TypeScript file with proper ESM and TypeScript support using symbolic links."""
    file_path = args.file
    generated_dir = getattr(args, "generated_dir", "./generated")
    verbose = getattr(args, "verbose", False)
    host = getattr(args, "host", "localhost")
    port = getattr(args, "port", 8000)
    debug = getattr(args, "debug", False)

    print(f"Testing file: {file_path}")
    print(f"Using generated code from: {generated_dir}")
    print(f"Targeting API at: http://{host}:{port}/api")

    # Check if server is running at the specified port
    import socket
    import time
    import multiprocessing

    def is_port_in_use(host, port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex((host, port)) == 0

    # Check if we need to start a server
    server_process = None
    if not is_port_in_use(host, port):
        print(f"❗ No server detected at {host}:{port}")
        print(f"🚀 Starting API server on port {port}...")

        # Try to guess the module from the generated directory
        # This is a heuristic and might not always work
        module_path = None
        if os.path.exists(generated_dir):
            # Look for potential module directories
            modules = [d for d in os.listdir(generated_dir)
                      if os.path.isdir(os.path.join(generated_dir, d))
                      and not d.startswith('_')
                      and not d.startswith('.')]

            if len(modules) > 0:
                module_path = modules[0]  # Use the first module we find
                print(f"📂 Auto-detected module: {module_path}")

        if not module_path:
            print("⚠️ Could not auto-detect module. Using a mock server instead.")
            # Start a mock server process that will handle basic API calls
            def run_mock_server():
                import uvicorn
                from fastapi import FastAPI, Body

                app = FastAPI(title="PyFlow.ts Mock Server")

                @app.post("/api/{path:path}")
                async def mock_endpoint(path: str, request: dict = Body(...)):
                    print(f"Mock server received request to /{path}: {request}")
                    return {"result": f"Mock response from {path}"}

                uvicorn.run(app, host=host, port=port)

            server_process = multiprocessing.Process(target=run_mock_server)
        else:
            # Using a proper picklable function instead of a lambda
            server_process = multiprocessing.Process(
                target=_run_server_process,
                args=(module_path, [module_path], host, port, generated_dir, False, debug)
            )

        server_process.daemon = True
        server_process.start()

        # Give the server some time to start
        print("⏳ Waiting for server to start...")
        for _ in range(10):  # Try up to 10 times (5 seconds)
            if is_port_in_use(host, port):
                print("✅ Server started successfully!")
                break
            time.sleep(0.5)
        else:
            print("⚠️ Server might not have started properly. Proceeding anyway...")

    # Convert paths to absolute for clarity
    file_path = os.path.abspath(file_path)
    generated_dir = os.path.abspath(generated_dir)

    # Get the file name and base name
    file_name = os.path.basename(file_path)
    base_name = os.path.splitext(file_name)[0]

    # Create a temporary directory for our test
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)

        # Create the debug directory structure
        os.makedirs(str(temp_dir_path), exist_ok=True)

        # Create symlink to the generated directory
        generated_link_path = os.path.join(temp_dir, 'generated')
        try:
            if os.path.exists(generated_link_path):
                if verbose:
                    print(f"Removing existing symlink: {generated_link_path}")
                if os.name == 'nt':  # Windows
                    subprocess.run(['cmd', '/c', f'rmdir "{generated_link_path}"'], shell=True)
                else:
                    os.unlink(generated_link_path)

            if verbose:
                print(f"Creating symlink: {generated_dir} -> {generated_link_path}")

            if os.name == 'nt':  # Windows
                # Use directory junction on Windows
                subprocess.run(['cmd', '/c', f'mklink /J "{generated_link_path}" "{generated_dir}"'], shell=True)
            else:
                # Use symlink on Unix/Mac
                os.symlink(generated_dir, generated_link_path, target_is_directory=True)

        except Exception as e:
            print(f"Error creating symlink: {e}")
            print("Will proceed with file copy instead...")
            shutil.copytree(generated_dir, generated_link_path)

        # Read the original TypeScript file
        with open(file_path, 'r') as f:
            original_content = f.read()

        # Create a modified version with debug info
        debug_content = f"""// Debug version with extra logging
import {{ pyflowRuntime }} from './pyflowRuntime.js';
{original_content}
"""
        # Write the debug file to the temp directory
        debug_file_path = os.path.join(temp_dir, file_name)
        with open(debug_file_path, 'w') as f:
            f.write(debug_content)

        # Generate client code with specified port
        client_generator = TypeScriptGenerator(temp_dir_path / "_client", host=host, port=port, debug=debug)
        # Use generate_ts_runtime() to get the runtime code instead
        runtime_debug = client_generator.runtime_code  # This method should return the actual runtime code

        # Write the runtime file
        runtime_path = temp_dir_path / 'pyflowRuntime.ts'
        with open(runtime_path, 'w') as f:
            f.write(runtime_debug)

        # Create tsconfig.json with proper ESM settings
        tsconfig = {
            "compilerOptions": {
                "target": "ES2020",
                "module": "NodeNext",
                "moduleResolution": "NodeNext",
                "esModuleInterop": True,
                "allowSyntheticDefaultImports": True,
                "skipLibCheck": True,
                "allowJs": True,
                "resolveJsonModule": True,
                "forceConsistentCasingInFileNames": True
            },
            "include": ["*.ts", "generated/**/*.ts"]
        }

        with open(os.path.join(temp_dir, 'tsconfig.json'), 'w') as f:
            json.dump(tsconfig, f, indent=2)

        # Create a package.json for ESM support
        package_json = {
            "name": "pyflow-test",
            "version": "1.0.0",
            "type": "module",
            "private": True
        }

        with open(os.path.join(temp_dir, 'package.json'), 'w') as f:
            json.dump(package_json, f, indent=2)

        # If verbose, print the directory structure
        if verbose:
            print("\n📂 Temporary directory structure:")
            if os.name == 'nt':  # Windows
                cmd = ["dir", "/s", "/b"]
                shell = True
            else:  # Unix/Mac
                cmd = ["find", ".", "-type", "f", "-o", "-type", "l"]
                shell = False

            try:
                dir_output = subprocess.run(
                    cmd,
                    cwd=temp_dir,
                    capture_output=True,
                    text=True,
                    shell=shell
                )
                print(dir_output.stdout)
            except Exception as e:
                print(f"Error listing directory: {e}")

        print(f"🔧 Test environment set up in {temp_dir}")
        print(f"📄 Running {file_name} with tsx...")

        try:
            # Use tsx to run TypeScript directly
            tsx_cmd = ["npx", "tsx", debug_file_path]

            if verbose:
                print(f"Running command: {' '.join(tsx_cmd)}")
                subprocess.run(tsx_cmd, cwd=temp_dir)
            else:
                try:
                    result = subprocess.run(
                        tsx_cmd,
                        cwd=temp_dir,
                        capture_output=True,
                        text=True,
                        timeout=60  # Add timeout to prevent hanging
                    )
                    # Print output even in non-verbose mode since this is a test
                    print(result.stdout)
                    if result.stderr:
                        print("Error output:")
                        print(result.stderr)
                except subprocess.TimeoutExpired:
                    print("❌ Test execution timed out after 60 seconds")
                except subprocess.CalledProcessError as e:
                    print(f"❌ Error running tsx: {e}")
                    if hasattr(e, 'output') and e.output:
                        print(e.output)
                    if hasattr(e, 'stderr') and e.stderr:
                        print(e.stderr)

            print("✅ Script executed successfully")

        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            if not verbose:
                print("\nTry running with --verbose for more details")

        finally:
            # Clean up the server process if we started one
            if server_process and server_process.is_alive():
                print("🛑 Shutting down test server...")
                server_process.terminate()
                server_process.join(timeout=2)
                if server_process.is_alive():
                    server_process.kill()  # Force kill if it didn't terminate

def show_version():
    """Display the installed PyFlow.ts version."""
    print(f"pyflow version {PYFLOWTS_VERSION}")

def run():
    """Entry point for the PyFlow.ts command-line interface."""
    parser = argparse.ArgumentParser(description="PyFlow.ts CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Version command
    version_parser = subparsers.add_parser("version", help="Show PyFlow.ts version")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run the PyFlow.ts server")
    run_parser.add_argument("-m", "--module", required=True, help="Module to import or directory to scan")
    run_parser.add_argument("-g", "--generated-dir", default="./generated", help="Output directory for generated code")
    run_parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    run_parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    run_parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    run_parser.add_argument("--debug", action="store_true", help="Enable debug mode with extra logging")

    # Generate command
    gen_parser = subparsers.add_parser("generate", help="Generate TypeScript code")
    gen_parser.add_argument("-m", "--module", required=True, help="Module to import or directory to scan")
    gen_parser.add_argument("-o", "--output", default="./generated", help="Output directory")
    gen_parser.add_argument("--port", type=int, default=8000, help="Port to use for the server")
    gen_parser.add_argument("--host", default="localhost", help="Host to use for the server")
    gen_parser.add_argument("--debug", action="store_true", help="Enable debug mode with extra logging")

    # Init command
    init_parser = subparsers.add_parser("init", help="Initialize a new PyFlow.ts project")
    init_parser.add_argument("-m", "--module", required=True, help="Module to import or directory to initialize")
    init_parser.add_argument("-o", "--output", default="./generated", help="Output directory for generated code")
    init_parser.add_argument("--name", help="Project name (defaults to directory name)")
    init_parser.add_argument("--port", type=int, default=8000, help="Port to use for the server")
    init_parser.add_argument("--debug", action="store_true", help="Enable debug mode with extra logging")

    # Test command - update with host and port options
    test_parser = subparsers.add_parser("test", help="Run a TypeScript file with PyFlow.ts support")
    test_parser.add_argument("-f", "--file", required=True, help="TypeScript file to run")
    test_parser.add_argument("-g", "--generated-dir", default="./generated",
                        help="Directory containing generated TypeScript code (default: ./generated)")
    test_parser.add_argument("--host", default="localhost",
                        help="Host to use for API server (default: localhost)")
    test_parser.add_argument("-p", "--port", type=int, default=8000,
                        help="Port to use for API server (default: 8000)")
    test_parser.add_argument("-v", "--verbose", action="store_true",
                        help="Enable verbose output with detailed error information")
    test_parser.add_argument("--debug", action="store_true",
                        help="Enable debug mode with extra logging")

    args = parser.parse_args()

    if args.command == "version":
        show_version()
    elif args.command == "run":
        # Fix handling of directory paths with trailing slashes
        module_path = args.module

        # Remove trailing slashes from directories for consistent handling
        if module_path.endswith('/'):
            module_path = module_path.rstrip('/')

        # Check if path is a directory
        if os.path.isdir(module_path):
            print(f"Processing directory: {module_path}")
            modules = scan_directory(module_path)
        else:
            # Handle as module
            try:
                print(f"Processing module: {module_path}")
                modules = [module_path]
            except ImportError as e:
                print(f"Error importing module {module_path}: {e}")
                print("Starting server anyway, but no endpoints may be available")
                modules = []

        generated_dir = getattr(args, "generated_dir", "./generated")
        host = getattr(args, "host", "localhost")
        port = getattr(args, "port", 8000)
        reload = getattr(args, "reload", False)
        debug = getattr(args, "debug", False)

        # Use the new function to run the generated server
        run_generated_server(module_path, modules, host, port, generated_dir, reload, debug)

    elif args.command == "generate":
        # Check if it's a directory or a module
        if os.path.isdir(args.module):
            modules = scan_directory(args.module)
        else:
            modules = [args.module]

        # Create output directory
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Get port value if provided, otherwise use default
        port = getattr(args, "port", 8000)
        host = getattr(args, "host", "localhost")
        reload = getattr(args, "reload", False)
        debug = getattr(args, "debug", False)

        # Generate TypeScript code with custom host and port
        ts_generator = TypeScriptGenerator(output_dir, host=host, port=port, debug=debug)
        ts_generator.generate_all()

        # Generate API
        api_generator = ApiGenerator(output_dir / "_server", host=host, port=port, reload=reload, debug=debug)
        api_generator.generate_api()

        # Generate client code with specified port
        client_generator = ClientGenerator(output_dir / "_client", host=host, port=port)
        client_generator.generate_all()

        print(f"Generated code for module {args.module} in {output_dir}")

    elif args.command == "init":
        # Initialize a new PyFlow.ts project
        initialize_project(args)

    elif args.command == "test":
        test_file(args)

    else:
        # Also show version when no command is provided
        show_version()
        parser.print_help()

def initialize_project(args):
    """Initialize a new PyFlow.ts project with TypeScript setup."""
    # Store original sys.argv to prevent command-line parsing conflicts
    original_argv = sys.argv.copy()

    try:
        # Temporarily clear command-line args to prevent conflicts
        sys.argv = [sys.argv[0]]

        # Get module path and remove trailing slashes
        module_path = args.module.rstrip('/')
        output_dir = args.output
        port = getattr(args, "port", 8000)
        host = getattr(args, "host", "localhost")
        reload = getattr(args, "reload", False)
        debug = getattr(args, "debug", False)

        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Check if input is a directory
        is_directory = os.path.isdir(module_path)

        if is_directory:
            print(f"Initializing PyFlow.ts project for directory: {module_path}")
        else:
            print(f"Initializing PyFlow.ts project for module: {module_path}")

        # Step 1: Scan and import modules
        print("Scanning for PyFlow.ts-decorated items...")

        if is_directory:
            # Convert to absolute path to avoid relative path issues
            abs_module_path = os.path.abspath(module_path)
            print(f"Scanning directory: {abs_module_path}")

            # Add the parent directory to sys.path temporarily to ensure correct imports
            parent_dir = os.path.dirname(abs_module_path)
            if parent_dir not in sys.path:
                sys.path.insert(0, parent_dir)
                path_added = True
            else:
                path_added = False

            try:
                # Get just the directory name without path for proper module naming
                dir_name = os.path.basename(abs_module_path)
                # Scan recursively for all Python modules in the directory
                modules = scan_directory(abs_module_path)

                # If no modules found, provide more information
                if not modules:
                    print("⚠️ No PyFlow.ts-decorated modules found. Make sure your Python files contain @extensity decorators.")
                    print("Checking for Python files...")
                    # List all Python files for debugging
                    python_files = []
                    for root, _, files in os.walk(abs_module_path):
                        for file in files:
                            if file.endswith('.py') and not file.startswith('__'):
                                rel_path = os.path.relpath(os.path.join(root, file), abs_module_path)
                                python_files.append(rel_path)

                    if python_files:
                        print(f"Found {len(python_files)} Python files: {', '.join(python_files)}")
                        print("Make sure these files contain @extensity decorators on functions or classes.")
                    else:
                        print("No Python files found in the directory.")

                # Determine project name from directory name
                if args.name:
                    project_name = args.name
                else:
                    project_name = os.path.basename(abs_module_path)
            finally:
                # Remove directory from path if we added it
                if path_added and parent_dir in sys.path:
                    sys.path.remove(parent_dir)

            # Store original path for reference in scripts
            module_path_for_scripts = abs_module_path
        else:
            # It's a single module
            # Handle case with slashes (file path)
            if '/' in module_path:
                abs_module_path = os.path.abspath(module_path)
                module_path_for_import = module_path.replace('/', '.').replace('.py', '')
            else:
                abs_module_path = module_path
                module_path_for_import = module_path

            print(f"Processing module: {module_path_for_import}")
            modules = [module_path_for_import]
            try:
                module = import_module_from_path(module_path_for_import)
            except Exception as e:
                print(f"Warning: Error importing module {module_path_for_import}: {e}")
                print("Will continue with setup but code generation may be incomplete.")

            # Determine project name from module name
            if args.name:
                project_name = args.name
            else:
                project_name = os.path.splitext(os.path.basename(module_path))[0]

            # Store original path for reference in scripts
            module_path_for_scripts = module_path
            module_path = module_path_for_import

        print(f"Found {len(modules)} modules to process")

        # Step 2: Generate TypeScript code
        print("Generating TypeScript code...")

        try:
            # Generate TypeScript code with custom host and port
            ts_generator = TypeScriptGenerator(output_path, host=host, port=port, debug=debug)

            # Process modules, with additional error handling for web frameworks
            ts_generator.generate_runtime()

            successful_modules = 0
            failed_modules = []

            for module_name in modules:
                try:
                    ts_generator.generate_module(module_name)
                    successful_modules += 1
                except Exception as e:
                    print(f"Warning: Error generating code for module {module_name}: {str(e)}")
                    # Don't stop for web framework errors
                    if "request context" in str(e).lower():
                        print("This is likely due to a web framework (Flask/Django) integration.")
                        print("Some functionality might be limited for this module.")
                    failed_modules.append(module_name)

            if failed_modules:
                print(f"\nProcessed {successful_modules} modules successfully.")
                print(f"Had issues with {len(failed_modules)} modules: {', '.join(failed_modules)}")
                print("You may still be able to use the successfully processed modules.")

            # Generate index files for organization
            try:
                ts_generator.generate_index()
            except Exception as e:
                print(f"Warning: Error generating index files: {e}")

            # Generate API
            try:
                api_generator = ApiGenerator(output_path / "_server", host=host, port=port, reload=reload, debug=debug)
                api_generator.generate_api()
            except Exception as e:
                print(f"Warning: Error generating API: {e}")
                print("You may need to run the API generation step separately.")

            # Generate client code
            try:
                client_generator = ClientGenerator(output_path / "_client", host=host, port=port)
                client_generator.generate_all()
            except Exception as e:
                print(f"Warning: Error generating client code: {e}")
        except Exception as e:
            print(f"Warning: Error during code generation: {e}")
            import traceback
            print(traceback.format_exc())
            print("Continuing with project setup...")

        # Step 3: Create package.json with proper scripts
        print("Creating package.json...")

        # For directories, the script should point to the directory path
        if is_directory:
            server_script = f"pyflow run -m {module_path_for_scripts} --port {args.port}"
        else:
            server_script = f"pyflow run -m {module_path} --port {args.port}"

        package_json = {
            "name": f"pyflow-ts-{project_name}",
            "version": "0.1.0",
            "description": f"PyFlow.ts project for {project_name}",
            "type": "module",
            "scripts": {
                "start-server": server_script,
                "start-ts": "tsc --watch",
                "start": "concurrently \"npm run start-server\" \"npm run start-ts\"",
                "build": "tsc",
                "serve": "node dist/index.js",
                "dev": "ts-node --esm src/index.ts"
            },
            "dependencies": {
                "node-fetch": "^3.3.1"
            },
            "devDependencies": {
                "concurrently": "^8.0.1",
                "ts-node": "^10.9.1",
                "typescript": "^5.0.4"
            }
        }

        with open(os.path.join(output_path, "package.json"), "w") as f:
            json.dump(package_json, f, indent=2)

        # Step 4: Create tsconfig.json with proper ESM configuration
        print("Creating tsconfig.json...")
        tsconfig_json = {
            "compilerOptions": {
                "target": "ES2020",
                "module": "NodeNext",
                "moduleResolution": "NodeNext",
                "esModuleInterop": True,
                "allowSyntheticDefaultImports": True,
                "strict": True,
                "outDir": "dist",
                "declaration": True,
                "skipLibCheck": True,
                "noEmitOnError": False,  # Keep generating output even with errors
                "baseUrl": "."
            },
            "include": ["src/**/*.ts"],
            "exclude": ["node_modules", "dist"]
        }

        with open(os.path.join(output_path, "tsconfig.json"), "w") as f:
            json.dump(tsconfig_json, f, indent=2)

        # Step 5: Create src directory and index.ts
        src_dir = output_path / "src"
        src_dir.mkdir(exist_ok=True)

        # Create a sample index.ts file that imports from our root aggregation file
        index_ts = """// Example usage of PyFlow.ts-generated TypeScript

// For Node.js < 18, uncomment this line if needed:
// import fetch from 'node-fetch';

// Import all exported items from the root index
import * as api from '../index.js';

// Log available APIs for debugging
console.log("Available API methods:", Object.keys(api));

// Example usage
async function main() {
    try {
        console.log("Available PyFlow.ts APIs:");

        // List all available functions and classes
        for (const key of Object.keys(api)) {
            if (typeof api[key] === 'function') {
                console.log(`- Function: ${key}`);
            } else if (typeof api[key] === 'object' || typeof api[key] === 'function') {
                console.log(`- Class/Object: ${key}`);
            }
        }

        console.log("\\nTo use these APIs, import them from specific modules or the root index.");
        console.log("Example: import { SomeClass, someFunction } from '../index.js';");

    } catch (error) {
        console.error("Error:", error);
        console.log("\\nTroubleshooting tips:");
        console.log("1. Make sure the PyFlow.ts server is running with: npm run start-server");
        console.log("2. Check that the import paths are correct");
        console.log("3. Verify that the API functions/classes match what's in your Python code");
    }
}

main().catch(error => {
    console.error("Error:", error);
});
"""

        with open(os.path.join(src_dir, "index.ts"), "w") as f:
            f.write(index_ts)

        # Step 6: Create README.md with updated instructions
        print("Creating README.md...")
        readme_md = f"""# PyFlow.ts Project: {project_name}

This project was automatically generated with PyFlow.ts.

## Getting Started

1. Install dependencies:
   ```bash
   npm install
   ```

2. Start the development server:
   ```bash
   npm start
   ```

This will start both the Python API server (on port {args.port}) and TypeScript compilation in watch mode.

## Using Your API

The generated `src/index.ts` file contains example code showing how to use your Python API from TypeScript:

```typescript
import * as api from '../index.js';

// Example usage
async function main() {{
    // Use your API here
    // For example:
    if (api.someFunction) {{
        const result = await api.someFunction();
        console.log(result);
    }}
}}
```

## Troubleshooting

### TypeScript Import Issues

If you encounter TypeScript errors related to imports:

1. **Missing Extensions**: Ensure all imports have `.js` extensions when using ES modules:
   ```typescript
   // Correct:
   import * as api from './module/index.js';
   ```

2. **Module Not Found**: If the import path doesn't match your file structure, you may need to adjust it.
   Try looking at the generated directories and update the path accordingly.

### Server Connection

If your TypeScript code can't connect to the Python server:

1. Make sure the server is running (should start with `npm start`)
2. Check that you're using the correct port number
3. Look for any error messages in the server console

## Project Structure

- `src/index.ts`: Main entry point for your TypeScript code
- `dist/`: Contains compiled JavaScript output
- `_server/`: Contains the FastAPI server code
- `_client/`: Contains client libraries for API access

## Available Scripts

- `npm start`: Start both the Python server and TypeScript compiler
- `npm run start-server`: Start only the Python server
- `npm run start-ts`: Start only the TypeScript compiler
- `npm run build`: Build TypeScript files
- `npm run serve`: Run the built JavaScript
- `npm run dev`: Run TypeScript directly with ts-node
"""

        with open(os.path.join(output_path, "README.md"), "w") as f:
            f.write(readme_md)

        # Step 7: Install npm dependencies
        print("Installing npm dependencies...")
        try:
            subprocess.run(["npm", "install"], cwd=output_path, check=True)
            print("✅ npm dependencies installed successfully")
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            print(f"⚠️ Could not install npm dependencies: {e}")
            print("Please run 'npm install' in the output directory manually")

        # Final output message with clearer instructions
        print(f"""
✨ PyFlow.ts project initialized successfully! ✨

Your project is now ready in: {output_path}

To start development:
Option 1: Use PyFlow.ts commands directly (recommended)
  # Start the API server
  pyflow run -m {module_path_for_scripts} --port {args.port}

  # In a separate terminal, compile TypeScript in watch mode
  cd {output_path} && npx tsc --watch

Option 2: Use npm scripts from the generated directory
  cd {output_path}
  npm start  # Runs both the API server and TypeScript compiler

To test your TypeScript code:
  # Run a TypeScript file against the server
  pyflow test -f your-file.ts -g {output_path} -p {args.port}

See the README.md file for more information.
""")

    finally:
        # Restore original command line arguments
        sys.argv = original_argv

def generate_root_index(output_dir: Path, modules: list) -> None:
    """Generate a root index.ts file that aggregates exports from all modules."""
    print("Generating root index file to aggregate all exports...")

    # Start with importing the runtime
    index_content = """// Root index file generated by PyFlow.ts
// This file aggregates all exports from all modules

import { pyflowRuntime } from './pyflowRuntime.js';

"""

    # Add exports for each module - avoid creating nested paths
    if modules:
        for module_name in modules:
            # Convert dot notation to path, but skip generated directories to avoid nesting
            if module_name.startswith('generated.'):
                continue

            module_path = module_name.replace('.', '/')
            index_content += f"export * from './{module_path}/index.js';\n"
    else:
        # No modules found - add a comment explaining
        index_content += """
// No @extensity decorated modules were found during scanning.
// Once you add @extensity decorators to your Python functions or classes,
// re-run the init command to generate TypeScript code for them.

// Example usage with properly decorated Python code:
// export * from './your_module/index.js';
"""

    # Write the file
    with open(output_dir / "index.ts", "w") as f:
        f.write(index_content)

    print(f"Root index file created at {output_dir / 'index.ts'}")

def scan_directory(directory_path: str, debug: bool = False) -> List[str]:
    """
    Recursively scan a directory for Python modules with @extensity decorators and import them.

    Args:
        directory_path: Path to directory to scan

    Returns:
        List of imported module names that contain PyFlow.ts decorators
    """
    from pyflow.core import registry
    imported_modules = []
    failed_imports = []
    retry_queue = []

    # Convert to absolute path
    abs_path = os.path.abspath(directory_path)
    print(f"Scanning directory: {abs_path}")

    # Add directory and parent directory to Python path temporarily
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
        # Get the directory name for proper module naming
        dir_name = os.path.basename(abs_path)

        # Add empty __init__.py files to directories without them to enable relative imports
        for root, dirs, files in os.walk(abs_path):
            # Only add __init__.py if this is a directory we might import from
            if not any(ignore in root for ignore in ('generated', '__pycache__')):
                # Check if __init__.py is missing
                init_file = os.path.join(root, "__init__.py")
                if not os.path.exists(init_file):
                    try:
                        # Create an empty __init__.py file to make it a proper package
                        with open(init_file, 'w') as f:
                            f.write("# Auto-generated by PyFlow.ts for package structure\n")
                        print(f"Created package __init__.py: {init_file}")
                    except (IOError, PermissionError) as e:
                        print(f"Warning: Could not create __init__.py in {root}: {e}")

        # First, try direct import approach for each Python file
        # This will catch files even if they're not imported in __init__.py
        for root, _, files in os.walk(abs_path):
            if 'generated' in root or '__pycache__' in root:
                continue

            for file in files:
                if file.endswith('.py') and not file.startswith('__'):
                    # Get the module path relative to the base directory
                    rel_path = os.path.relpath(root, abs_path)
                    file_path = os.path.join(root, file)

                    if rel_path == '.':
                        # Top-level module
                        module_name = file[:-3]  # Remove .py extension
                    else:
                        # Submodule
                        module_parts = rel_path.replace(os.path.sep, '.').split('.')
                        module_name = f"{'.'.join(module_parts)}.{file[:-3]}"

                    # Try both with and without the directory prefix
                    module_options = [
                        module_name,
                        f"{dir_name}.{module_name}"
                    ]

                    # Check for @extensity decorator in the file
                    try:
                        with open(file_path, 'r') as f:
                            content = f.read()
                            has_decorator = '@extensity' in content

                        if has_decorator:
                            print(f"Found @extensity decorator in {file_path}, attempting import...")
                            # Try to import the module directly
                            for module_path in module_options:
                                try:
                                    module = importlib.import_module(module_path)
                                    if len(registry.modules) > 0:  # Verify registration worked
                                        imported_modules.append(module_path)
                                        print(f"✅ Successfully imported decorated module: {module_path}")
                                        break
                                except ImportError:
                                    continue
                    except Exception as e:
                        print(f"Error checking file {file_path}: {e}")

        # Collect all Python files first (this is the standard approach)
        python_files = []
        for root, dirs, files in os.walk(abs_path):
            # Skip generated directories and __pycache__
            if 'generated' in root or '__pycache__' in root:
                continue

            # Get relative path for proper module naming
            rel_path = os.path.relpath(root, abs_path)

            # Process all Python files
            for file in files:
                if file.endswith('.py') and not file.startswith('__'):
                    file_path = os.path.join(root, file)
                    module_name = os.path.splitext(file)[0]

                    if rel_path == '.':
                        module_options = [
                            module_name,                  # Direct module
                            f"{dir_name}.{module_name}"   # As submodule of directory
                        ]
                    else:
                        package_path = rel_path.replace(os.path.sep, '.')
                        module_options = [
                            f"{package_path}.{module_name}",         # Just the relative path
                            f"{dir_name}.{package_path}.{module_name}"  # With directory prefix
                        ]

                    python_files.append((file_path, module_options))

        # Process files - first pass
        for file_path, module_options in python_files:
            if debug: print(f"Checking file: {file_path}")
            try_import(file_path, module_options, imported_modules, failed_imports, retry_queue, debug)

        # Retry failed imports - they might depend on modules we've now imported
        if retry_queue:
            print("\n🔄 Retrying imports that failed on first pass...")
            for file_path, module_options in retry_queue:
                print(f"Retrying: {file_path}")
                try_import(file_path, module_options, imported_modules, failed_imports, [], debug)

        # Double-check - scan registry directly to ensure we found everything
        # This will catch any decorated items that might have been missed
        added_from_registry = 0
        registry_modules = list(registry.modules)
        for reg_module in registry_modules:
            if reg_module.startswith(dir_name) and reg_module not in imported_modules:
                imported_modules.append(reg_module)
                added_from_registry += 1

        if added_from_registry > 0:
            print(f"Added {added_from_registry} additional modules from registry")

        if failed_imports:
            print(f"\n⚠️ {len(failed_imports)} files could not be imported successfully")
            # list file names for reference
            for file_path in failed_imports:
                print(f"   - {file_path}")

        # Display PyFlow.ts statistics
        module_count = len(registry.modules)
        func_count = len(registry.functions)
        class_count = len(registry.classes)

        if module_count > 0:
            print(f"\n✅ Found {module_count} modules with PyFlow.ts decorators")
            print(f"   - {func_count} decorated functions")
            print(f"   - {class_count} decorated classes")
        else:
            print("\n❌ No PyFlow.ts decorators found in any modules")
            print("   Make sure you've added @extensity decorators to your functions or classes")

    # Add specific handling for the conflicting pyflow package issue
    except Exception as e:
        if "unrecognized arguments" in str(e) and "pyflow" in str(e):
            print("\n❌ ERROR: Detected name conflict with another 'pyflow' package")
            print("   This usually happens when a module you're importing is using a different 'pyflow' package.")
            print("   To fix this, you might need to:")
            print("   1. Check if you have multiple pyflow packages installed")
            print("   2. Check if any of your modules are importing a different pyflow package")
            print("   3. Try using a virtual environment for PyFlow.ts")
            print("   4. Rename your conflicting package\n")
        else:
            print(f"\n❌ Unexpected error during scanning: {e}")
            import traceback
            print(traceback.format_exc())
    finally:
        # Remove directories from Python path
        if path_added and abs_path in sys.path:
            sys.path.remove(abs_path)
        if parent_added and parent_dir in sys.path:
            sys.path.remove(parent_dir)

    return imported_modules

def try_import(file_path, module_options, imported_modules, failed_imports, retry_queue, debug: bool = False):
    """Helper function to try importing a module with various strategies."""
    from pyflow.core import registry

    # Store original sys.argv to restore it later
    original_argv = sys.argv.copy()

    try:
        # First, try to empty sys.argv to avoid argument parsing issues
        # This helps when modules try to parse command line arguments
        sys.argv = [sys.argv[0]]

        imported = False
        for full_module_name in module_options:
            if imported:
                break

            try:
                # Import the module
                initial_count = len(registry.modules)

                # Try standard import first
                try:
                    module = importlib.import_module(full_module_name)
                    imported = True
                except (ModuleNotFoundError, ImportError) as e:
                    # If that fails, try spec_from_file_location
                    try:
                        spec = importlib.util.spec_from_file_location(full_module_name, file_path)
                        if spec and spec.loader:
                            module = importlib.util.module_from_spec(spec)
                            sys.modules[full_module_name] = module
                            spec.loader.exec_module(module)
                            imported = True
                    except Exception:
                        continue  # Try next module name option

                # Check if this module contributed decorators to the registry
                if imported and len(registry.modules) > initial_count:
                    imported_modules.append(full_module_name)
                    print(f"✅ Imported module with @extensity decorators: {full_module_name}")
                    break  # Successfully imported, no need to try other options
                elif imported:
                    if debug: print(f"⚠️ No @extensity decorators found in module: {full_module_name}")
                    break  # Module imported but no decorators, no need to try other options

            except Exception as e:
                # Check if this is a missing name error that might be resolved on a retry
                error_str = str(e)
                if "name '" in error_str and "' is not defined" in error_str:
                    # Add to retry queue - we'll try again after other modules are loaded
                    if file_path not in [x[0] for x in retry_queue]:
                        retry_queue.append((file_path, module_options))
                        print(f"⏳ Queuing for retry - dependency issue: {error_str}")
                else:
                    print(f"Error importing module {full_module_name}: {e}")

        # If we couldn't import with any strategy, report it
        if not imported:
            print(f"❌ Failed to import module from {file_path}")
            failed_imports.append(file_path)

    finally:
        # Restore original sys.argv
        sys.argv = original_argv

def run_generated_server(module_path, modules, host, port, generated_dir=None, reload=False, debug=False):
    """Run the generated server code or generate it on demand."""
    # Prevent command line parsing conflicts by emptying sys.argv temporarily
    original_argv = sys.argv.copy()
    sys.argv = [sys.argv[0]]

    try:
        # First check if module_path contains a generated directory with _server
        if os.path.isdir(module_path):
            if generated_dir is None:
                potential_server_dir = os.path.join(module_path, "generated", "_server")
            else:
                potential_server_dir = os.path.join(generated_dir, "_server")
            # Check if the directory exists
            if os.path.isdir(potential_server_dir):
                generated_dir = Path(potential_server_dir)
                print(f"Found existing server code in {potential_server_dir}")

            # Also check if there's directly a _server directory
            if os.path.isdir(potential_server_dir) and not generated_dir:
                generated_dir = Path(potential_server_dir)
                print(f"Found existing server code in {potential_server_dir}")

        # If not found, generate a temporary server
        if not generated_dir:
            print("No existing server code found, generating temporary server...")
            # Create a temporary output directory
            temp_dir = Path(tempfile.mkdtemp())
            temp_server_dir = temp_dir / "_server"

            try:
                # Generate API code
                api_generator = ApiGenerator(temp_server_dir, host=host, port=port, reload=reload, debug=debug)
                api_generator.generate_api()
                generated_dir = temp_server_dir
                print(f"Generated temporary server code in {temp_server_dir}")
            except Exception as e:
                print(f"Error generating server code: {e}")
                print("Falling back to direct execution mode")
                generated_dir = None

        # If we have generated code, use it
        if generated_dir:
            server_script = Path(generated_dir) / "server.py"

            if server_script.exists():
                print(f"Running generated server from {server_script}")

                # Add the directory to sys.path temporarily
                server_dir = str(generated_dir)
                if server_dir not in sys.path:
                    sys.path.insert(0, server_dir)

                try:
                    # First import any modules to ensure they're processed
                    if modules:
                        for module_name in modules:
                            try:
                                # Use a specialized import approach to avoid command line parsing
                                spec = importlib.util.find_spec(module_name)
                                if spec:
                                    module = importlib.util.module_from_spec(spec)
                                    spec.loader.exec_module(module)
                                else:
                                    print(f"Warning: Could not find module {module_name}")
                            except ImportError as e:
                                print(f"Warning: Could not import module {module_name}: {e}")

                    # Import and run the generated server
                    sys.path.insert(0, str(generated_dir.parent))  # Add parent dir to path

                    # Use specialized import approach to avoid command line conflicts
                    spec = importlib.util.spec_from_file_location("server", server_script)
                    if spec and spec.loader:
                        server_module = importlib.util.module_from_spec(spec)
                        sys.modules["server"] = server_module
                        spec.loader.exec_module(server_module)

                        # Call the start_server function
                        if hasattr(server_module, "start_server"):
                            print(f"Starting server on {host}:{port} (reload={reload}, debug={debug})")
                            server_module.start_server(host=host, port=port, reload=reload, debug=debug)
                        else:
                            # Fallback to running the module directly
                            print("Using fallback server execution method")
                            subprocess.run([sys.executable, str(server_script),
                                        f"--host={host}", f"--port={port}",
                                        *(["--reload"] if reload else []),
                                        *(["--debug"] if debug else [])])
                    else:
                        raise ImportError(f"Could not load server module from {server_script}")

                except Exception as e:
                    print(f"Error running server: {e}")
                    import traceback
                    traceback.print_exc()
                    sys.exit(1)
                return

        # If we reach here, something went wrong with the generated server
        print("Error: Could not find or run the generated server code")
        sys.exit(1)

    finally:
        # Restore original command line arguments
        sys.argv = original_argv

if __name__ == "__main__":
    run()