# PyFlow.ts

<img src="https://raw.githubusercontent.com/ExtensityAI/symbolicai/refs/heads/main/assets/images/banner.png">

-----

[![PyPI version](https://img.shields.io/pypi/v/pyflow-ts.svg)](https://pypi.org/project/pyflow-ts/)
[![Python versions](https://img.shields.io/pypi/pyversions/pyflow-ts.svg)](https://pypi.org/project/pyflow-ts/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[![Twitter](https://img.shields.io/twitter/url/https/twitter.com/dinumariusc.svg?style=social&label=Follow%20%40DinuMariusC)](https://twitter.com/DinuMariusC) [![Twitter](https://img.shields.io/twitter/url/https/twitter.com/symbolicapi.svg?style=social&label=Follow%20%40ExtensityAI)](https://twitter.com/ExtensityAI)
[![Discord](https://img.shields.io/discord/768087161878085643?label=Discord&logo=Discord&logoColor=white)](https://discord.gg/QYMNnh9ra8) [![Hits](https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https%3A%2F%2Fgithub.com%2FXpitfire%2Fpyflowts&count_bg=%2379C83D&title_bg=%23555555&icon=&icon_color=%23E7E7E7&title=hits&edge_flat=false)](https://hits.seeyoufarm.com) [![GitHub forks](https://img.shields.io/github/forks/ExtensityAI/PyFlow.ts.svg?style=social&label=Fork&maxAge=2592000)](https://GitHub.com/ExtensityAI/PyFlow.ts) [![GitHub stars](https://img.shields.io/github/stars/ExtensityAI/PyFlow.ts.svg?style=social&label=Star&maxAge=2592000)](https://GitHub.com/ExtensityAI/PyFlow.ts/stargazers/)


**PyFlow.ts** - Bridge Python and TypeScript with ease. Use simple decorators to expose Python functions, methods, and classes to TypeScript with full type safety.

## Why PyFlow.ts Matters

Data scientists and machine learning engineers work predominantly in Python, while web developers typically build frontends in TypeScript/JavaScript. This creates a painful gap in the development workflow:

Many teams spend days to weeks creating REST APIs, writing OpenAPI specs, generating clients, and managing infrastructure - just to connect Python ML models to frontend applications.

**With PyFlow.ts**: Simply decorate your Python functions and classes with `@extensity` and extend them beyond the boarders of Python environment to make them available in TypeScript with full type safety. This eliminates the traditional barriers between data science and frontend development:

- **Machine Learning to Production in Minutes**: Deploy trained ML models to production frontends with zero API boilerplate
- **Unified Development Experience**: Data scientists can focus on Python algorithms while frontend developers consume them as if they were native TypeScript
- **Frictionless Updates**: When Python implementations change, TypeScript interfaces update automatically - no API versioning headaches
- **Fast Iteration Cycles**: Experiments go from notebook to production-ready web app in record time, enabling rapid prototyping

PyFlow.ts is particularly valuable for ML-powered applications, where Python's rich ecosystem meets the need for responsive, type-safe web interfaces.

## Features

- ✨ **Simple Decorators**: Mark Python objects with `@extensity` to expose them to TypeScript
- 🔄 **Automatic Type Conversion**: Python type annotations are mapped to TypeScript types
- 🚀 **Zero Boilerplate**: No manual API endpoints or TypeScript interfaces needed
- 🔒 **Type Safety**: Full TypeScript type definitions for Python objects
- 🌐 **FastAPI Backend**: Generated API server for seamless communication
- 📦 **Easy Integration**: Works with any Python codebase

## Installation

PyFlow.ts requires **Python 3.10+** and can be installed via pip:

```bash
pip install pyflow-ts
```

## Quick Test Guide

Here's how to quickly test PyFlow.ts with your Python code:

### 1. Initialize and Generate TypeScript Code

Generate TypeScript code from your Python module:

```bash
pyflow init -m examples/basic/calculator.py -o examples/basic/generated --port 8002
```

This command:
- Takes your Python module (`examples/basic/calculator.py`)
- Generates TypeScript code in the specified output directory (`examples/basic/generated`)
- Configures the API server to use port 8002

### 2. Run the API Server

Start the API server to expose your Python functions:

```bash
pyflow run -m examples.basic.calculator
```

This command:
- Imports your Python module using the module path notation
- Starts a FastAPI server that exposes your decorated functions and classes
- Runs on port 8000 by default (or the port specified during initialization)

### 3. Test Your TypeScript Code

Test your TypeScript code with the `test` command:

```bash
pyflow test -f examples/basic/calculator-app.ts -g examples/basic/generated -p 8002 -v
```

This command:
- Runs the specified TypeScript file (`examples/basic/calculator-app.ts`)
- Uses the generated TypeScript code in the directory (`examples/basic/generated`)
- Connects to the API server on the specified port (8002)
- Provides verbose output with the `-v` flag

The `test` command automatically sets up a temporary environment with proper TypeScript and ESM support, allowing you to quickly test your code without manual configuration.

# Quick Start Guide

This quick start guide will walk you through using PyFlow.ts to bridge Python and TypeScript, using both the traditional approach and the new streamlined initialization process.

## Quick Start with Init Command

### 1. Initialize Your Project

The easiest way to get started is to use the `init` command, which sets up everything you need:

```bash
# Initialize a project for your Python module
pyflow init -m your_module.py
```

This single command:
- Generates TypeScript code from your Python code
- Creates a complete Node.js project structure
- Sets up package.json with necessary dependencies
- Configures TypeScript correctly
- Creates a sample index.ts file
- Installs all required npm packages

## Using Decorators

### Decorating Classes

When you decorate a class with `@extensity`, all its public methods and attributes are automatically exported to TypeScript:

```python
@extensity
class Calculator:
    history: List[Dict[str, float]] = []

    def calculate(self, a: float, b: float, operation: str) -> float:
        # This method is automatically exported, no decorator needed
        result = a + b if operation == "add" else a - b
        self.history.append({"a": a, "b": b, "result": result})
        return result

    def _internal_method(self):
        # This won't be exported because it starts with an underscore
        pass
```

### Decorating Individual Methods

Only use method-level decorators when you want to expose specific methods from a class:

```python
class DataService:
    def __init__(self):
        self.data = {}

    @extensity
    def get_public_data(self) -> Dict:
        # Only this method will be exported
        return {"public": "data"}

    def internal_process(self):
        # This won't be exported
        pass
```

### Decorating Functions

For standalone functions, simply add the decorator:

```python
@extensity
def add(a: float, b: float) -> float:
    return a + b
```

### Avoid Redundancy

Do not decorate both a class and its methods - this is redundant:

```python
@extensity  # ✅ This is sufficient
class Example:

    # ❌ Don't do this!
    @extensity  # Redundant - the class is already decorated
    def some_method(self) -> str:
        return "example"
```

When a class is decorated with `@extensity`, all its public methods are automatically exported without needing individual decorators.

### Manual Class Registration

In some cases, you might want to manually register a class instead of using the `@extensity` decorator. This can be useful for dynamically created classes or when you need more control over the exposed methods and registration process:

```python
from pyflow.core import registry

class DynamicCalculator:
    def add(self, a: float, b: float) -> float:
        return a + b

    @extensity
    def subtract(self, a: float, b: float) -> float:
        return a - b

# Manually register the class
registry.register_class(DynamicCalculator)
```

## Detailed Example: Calculator

Let's walk through a complete example to understand the full workflow.

### 1. Decorate your Python code

```python
# calculator.py
from pyflow import extensity
from typing import List, Dict

@extensity
def add(a: float, b: float) -> float:
    return a + b

@extensity
def subtract(a: float, b: float) -> float:
    return a - b

@extensity
class Calculator:
    history: List[Dict[str, float]] = []

    def calculate(self, a: float, b: float, operation: str) -> float:
        pass # rest of the implementation

    def get_history(self) -> List[Dict[str, float]]:
        return self.history

    def clear_history(self) -> None:
        self.history = []
```

### 2. Initialize the project (recommended)

```bash
# Initialize a complete project
pyflow init -m calculator.py -o ./generated
```

OR generate the TypeScript code manually:

```bash
# Generate TypeScript code only
pyflow generate -m calculator.py -o ./generated
```

If you used `init`, the the a node project is initialized with npm dependencies.

Otherwise, it generates TypeScript code of the Python module.

### 3. Run the API server

To run the API server you can use the `run` command in the local directory:

```bash
pyflow run -m ./
```

### 4. Use the generated TypeScript code

The generated `index.ts` will already have imports set up. For our calculator example, you would use it like this:

```typescript
// index.ts
import { add, subtract, multiply, divide, Calculator } from './generated/calculator/index.js';

async function runCalculator() {
  console.log("Basic operations:");
  console.log(`5 + 3 = ${await add(5, 3)}`);
  console.log(`10 - 4 = ${await subtract(10, 4)}`);

  console.log("\nUsing Calculator class:");
  const calculator = new Calculator();

  // Perform calculations
  console.log(`Calculator: 10 + 5 = ${await calculator.calculate(10, 5, "add")}`);
  console.log(`Calculator: 10 - 5 = ${await calculator.calculate(10, 5, "subtract")}`);
}

runCalculator().catch(console.error);
```

## Expected Output

Running the calculator example should produce output like:

```
Basic operations:
5 + 3 = 8
10 - 4 = 6

Using Calculator class:
Calculator: 10 + 5 = 15
Calculator: 10 - 5 = 5
```

## Next Steps

- Explore advanced features like directory scanning
- Try creating your own classes and functions with the `@extensity` decorator
- Check out the examples directory for more complex use cases

## How It Works

PyFlow.ts uses a combination of Python introspection, FastAPI, and TypeScript code generation:

1. **Registration**: The `@extensity` decorator registers Python functions and classes in a global registry
2. **API Generation**: A FastAPI application is generated with endpoints for each registered item
3. **TypeScript Generation**: TypeScript interfaces, classes, and functions are generated based on Python type annotations
4. **Runtime Bridge**: The TypeScript code communicates with the Python API server to execute the Python code

## Advanced Usage

### Custom Type Mappings

PyFlow.ts automatically maps Python types to TypeScript types. Common mappings include:

| Python Type | TypeScript Type |
|-------------|----------------|
| `str` | `string` |
| `int`, `float` | `number` |
| `bool` | `boolean` |
| `list[T]`, `List[T]` | `T[]` |
| `dict[K, V]`, `Dict[K, V]` | `Record<K, V>` |
| `tuple`, `Tuple` | Array or typed tuple |
| `Union[T, U]` | `T \| U` |
| `Optional[T]` | `T \| null` |
| Classes | Interfaces with the same name |

## CLI Options

```
pyflow run -m MODULE [--generate-dir GENERATE_DIR] [--host HOST] [--port PORT] [--reload]
pyflow generate -m MODULE -o OUTPUT_DIR
```

### Run command

- `-m, --module`: Module to import, file path, or directory to scan (required)
- `-g, --generate-dir`: Directory containing generated TypeScript code (optional)
- `--host`: Host to bind to (default: 0.0.0.0)
- `--port`: Port to bind to (default: 8000)
- `--reload`: Enable auto-reload for development

If the specified port is already in use, PyFlow.ts will automatically attempt to find an available port.

### Generate command

- `-m, --module`: Module to import, file path, or directory to scan (required)
- `-o, --output`: Output directory for generated TypeScript code (required)

## Directory Scanning

PyFlow.ts can recursively scan directories to find and process Python files containing `@extensity` decorators.

### Scanning a Directory

To process all Python files in a directory:

```bash
# Process a single directory
pyflow generate -m ./your_directory -o ./generated

# Run server for all modules in a directory
pyflow run -m ./your_directory -g ./generated
```

When specifying a directory, PyFlow.ts will:

1. Recursively scan all subdirectories
2. Import all Python files (excluding `__init__.py` and similar)
3. Register any classes or functions decorated with `@extensity`
4. Generate TypeScript interfaces and API endpoints for all registered items

This is particularly useful for larger projects with multiple modules.

### Importing Local Files

PyFlow.ts can also import Python files directly without requiring them to be in the Python path:

```bash
# Import a specific file
pyflow generate -m ./path/to/your_file.py -o ./generated

# Run server for a specific file
pyflow run -m ./path/to/your_file.py
```

## Port Configuration

### Using a Custom Port

You can specify a custom port for the PyFlow.ts server:

```bash
pyflow run -m your_module --port 8080
```

### Automatic Port Selection

If the specified port is already in use, PyFlow.ts will automatically attempt to find an available port:

```
$ pyflow run -m your_module
Warning: Port 8000 is already in use.
Using alternative port 8001 instead.
```

This makes it easier to run multiple instances or work in environments where the default port might be occupied by other services.

## Requirements

- Python 3.10+
- TypeScript 4.5+ (for frontend usage)

## Comparison with Other Tools

While several technologies exist for exporting Python models to other environments, each has distinct advantages and limitations:

### ONNX (Open Neural Network Exchange)

**ONNX** converts ML models for cross-platform deployment but has significant limitations:
- ✅ Good for deploying trained models to specific hardware/platforms
- ✅ Works well for standard architectures and established operations
- ❌ Often lags behind cutting-edge PyTorch/TensorFlow features
- ❌ Complex custom layers frequently require special handling
- ❌ Limited to model inference only, not full application logic

### TensorFlow.js, PyTorch Mobile, etc.

**Framework-specific export tools** have similar constraints:
- ✅ Optimized for their specific runtime environments
- ✅ Direct integration with their ecosystem
- ❌ Limited to their specific framework (vendor lock-in)
- ❌ Feature gap between Python and exported versions
- ❌ Require significant rework for custom operations

### Where PyFlow.ts Shines

**PyFlow.ts** takes a fundamentally different approach:
- ✅ **No Conversion Limitations**: Uses the actual Python code, not a conversion
- ✅ **Always Current**: Access the latest ML techniques immediately, not months later
- ✅ **Complete Workflow**: Exposes your entire application logic, not just the model
- ✅ **Custom Operations**: Works with any Python code, not just standard operations
- ✅ **Rapid Prototyping**: Change the Python implementation without redoing the API

**When to use PyFlow.ts:**
- When you need rapid iteration between research and production
- When your models use cutting-edge features not yet supported in export formats
- When you need the full Python ML ecosystem, not just the model inference
- For applications where TypeScript/JavaScript is the frontend but Python handles ML

**When other tools might be better:**
- When you need maximum inference performance on edge devices
- For fully offline mobile applications with no API connection
- When deployment constraints prohibit running a Python server

PyFlow.ts bridges the gap between Python's ML ecosystem leadership and TypeScript's frontend capabilities, focusing on developer productivity and deployment speed rather than edge-case performance optimization.

## License

[MIT License](LICENSE)

## Contributing

Contributions are welcome! Please check out our [contribution guidelines](CONTRIBUTING.md) for details.

## Acknowledgements

PyFlow.ts was inspired by various Python-TypeScript bridging solutions, including FastAPI's automatic OpenAPI generation and TypeScript client code generators.
