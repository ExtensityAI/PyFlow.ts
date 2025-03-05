import unittest
import tempfile
import shutil
from pathlib import Path
from pyflow.generators.ts_generator import TypeScriptGenerator
from pyflow.generators.api_generator import ApiGenerator
from pyflow.generators.client_generator import ClientGenerator
from pyflow.core import Registry

class TestGenerators(unittest.TestCase):
    def setUp(self):
        # Clear the singleton instance for testing
        Registry._instance = None
        self.registry = Registry()

        # Create a temporary directory for output
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        # Remove the temporary directory
        shutil.rmtree(self.temp_dir)

    def test_ts_generator_runtime(self):
        """Test generating the TypeScript runtime."""
        generator = TypeScriptGenerator(self.temp_dir, host="localhost", port=8000)
        generator.generate_runtime()

        runtime_file = self.temp_dir / "pyflowRuntime.ts"
        self.assertTrue(runtime_file.exists())

        with open(runtime_file, "r") as f:
            content = f.read()
            self.assertIn("export interface PyFlowRuntime", content)
            self.assertIn("callFunction", content)
            self.assertIn("callMethod", content)
            self.assertIn(f"'http://{generator.host}:{generator.port}/api'", content)

    def test_api_generator(self):
        """Test generating the API endpoints."""
        # Register a test function and class
        def test_func(a: int, b: str) -> bool:
            return True

        class TestClass:
            attr1: str = "test"

            def method1(self, a: int) -> str:
                return "test"

        self.registry.register_function(test_func, "test_module")
        self.registry.register_class(TestClass, "test_module")

        # Generate API
        generator = ApiGenerator(self.temp_dir)
        generator.generate_api()

        api_file = self.temp_dir / "api.py"
        server_file = self.temp_dir / "server.py"

        self.assertTrue(api_file.exists())
        self.assertTrue(server_file.exists())

        with open(api_file, "r") as f:
            content = f.read()
            self.assertIn("app = FastAPI", content)
            self.assertIn("/api/call-function", content)
            self.assertIn("/api/call-method", content)

    def test_client_generator(self):
        """Test generating the client code."""
        generator = ClientGenerator(self.temp_dir)
        generator.generate_all()

        py_client_file = self.temp_dir / "client.py"
        js_client_file = self.temp_dir / "client.js"

        self.assertTrue(py_client_file.exists())
        self.assertTrue(js_client_file.exists())

        with open(py_client_file, "r") as f:
            content = f.read()
            self.assertIn("class PyFlowClient", content)
            self.assertIn("call_function", content)
            self.assertIn("call_method", content)

        with open(js_client_file, "r") as f:
            content = f.read()
            self.assertIn("PyFlowRuntime", content)
            self.assertIn("callFunction", content)
            self.assertIn("callMethod", content)