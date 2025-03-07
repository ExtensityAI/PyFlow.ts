import unittest
from pyflow.utils.type_converter import (
    python_type_to_ts,
    generate_ts_interface,
    generate_ts_function
)
from typing import List, Dict, Any, Union, Optional, Tuple, Set

class TestTypeConversion(unittest.TestCase):
    def test_primitive_type_conversion(self):
        """Test conversion of primitive Python types to TypeScript."""
        self.assertEqual(python_type_to_ts(str), "string")
        self.assertEqual(python_type_to_ts(int), "number")
        self.assertEqual(python_type_to_ts(float), "number")
        self.assertEqual(python_type_to_ts(bool), "boolean")
        self.assertEqual(python_type_to_ts(None), "null")

    def test_collection_type_conversion(self):
        """Test conversion of collection Python types to TypeScript."""
        self.assertEqual(python_type_to_ts(list), "any[]")
        self.assertEqual(python_type_to_ts(dict), "Record<string, any>")
        self.assertEqual(python_type_to_ts(tuple), "any[]")
        self.assertEqual(python_type_to_ts(set), "Set<any>")

    def test_generic_type_conversion(self):
        """Test conversion of generic Python types to TypeScript."""
        self.assertEqual(python_type_to_ts(List[str]), "string[]")
        self.assertEqual(python_type_to_ts(Dict[str, int]), "Record<string, number>")
        self.assertEqual(python_type_to_ts(Union[str, int]), "string | number")
        self.assertEqual(python_type_to_ts(Optional[str]), "string | null")
        self.assertEqual(python_type_to_ts(Tuple[str, int]), "[string, number]")
        self.assertEqual(python_type_to_ts(Set[str]), "Set<string>")

    def test_generate_ts_interface(self):
        """Test generating a TypeScript interface from a Python class."""
        class TestClass:
            attr1: str = "test"
            attr2: int = 123
            attr3: List[str] = ["a", "b", "c"]

        interface = generate_ts_interface(TestClass)

        self.assertIn("export interface TestClass", interface)
        self.assertIn("attr1: string", interface)
        self.assertIn("attr2: number", interface)
        self.assertIn("attr3: string[]", interface)

    def test_generate_ts_function(self):
        """Test generating a TypeScript function from a Python function."""
        def test_func(a: int, b: str = "default") -> Dict[str, Any]:
            return {"a": a, "b": b}

        ts_function = generate_ts_function(test_func)

        self.assertIn("export function test_func", ts_function)
        self.assertIn("a: number", ts_function)
        self.assertIn("b: string = 'default'", ts_function)
        self.assertIn("Record<string, any>", ts_function)
