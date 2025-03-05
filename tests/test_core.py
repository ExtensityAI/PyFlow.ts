import unittest
from pyflow.core import Registry
from typing import List

class TestRegistry(unittest.TestCase):
    def setUp(self):
        # Create a fresh registry for each test
        self.registry = Registry()
        # Clear the singleton instance for testing
        Registry._instance = None

    def test_singleton(self):
        """Test that Registry is a singleton."""
        registry1 = Registry()
        registry2 = Registry()
        self.assertIs(registry1, registry2)

    def test_register_function(self):
        """Test registering a function."""
        def test_func(a: int, b: str) -> bool:
            return True

        self.registry.register_function(test_func, "test_module")

        # Use fully qualified name in the assertion
        function_key = f"{self.__class__.__name__}.test_register_function.<locals>.test_func"

        self.assertIn(function_key, self.registry.functions)
        self.assertEqual(self.registry.functions[function_key]["func"], test_func)
        self.assertEqual(self.registry.functions[function_key]["module"], "test_module")
        self.assertIn("a", self.registry.functions[function_key]["type_hints"])
        self.assertIn("b", self.registry.functions[function_key]["type_hints"])
        self.assertIn("return", self.registry.functions[function_key]["type_hints"])

    def test_register_class(self):
        """Test registering a class."""
        class TestClass:
            attr1: str = "test"
            attr2: int = 123

            def method1(self, a: int) -> str:
                return "test"

            def method2(self, b: str) -> List[int]:
                return [1, 2, 3]

        self.registry.register_class(TestClass, "test_module")

        # Use fully qualified name in the assertion
        class_key = f"{self.__class__.__name__}.test_register_class.<locals>.TestClass"

        self.assertIn(class_key, self.registry.classes)
        self.assertEqual(self.registry.classes[class_key]["cls"], TestClass)
        self.assertEqual(self.registry.classes[class_key]["module"], "test_module")
        self.assertIn("method1", self.registry.classes[class_key]["methods"])
        self.assertIn("method2", self.registry.classes[class_key]["methods"])
        self.assertIn("attr1", self.registry.classes[class_key]["class_vars"])
        self.assertIn("attr2", self.registry.classes[class_key]["class_vars"])
