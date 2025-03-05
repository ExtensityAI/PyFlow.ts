# Examples demonstrating proper decorator usage

# 1. Decorating a class (preferred way)
# When you decorate a class, all public methods and attributes are automatically exported
# This is the recommended approach for classes
from pyflow import extensity
from typing import List, Dict

@extensity
class Calculator:
    history: List[Dict[str, float]] = []

    def __init__(self):
        self.history = []

    def calculate(self, a: float, b: float, operation: str) -> float:
        # No need to decorate this method, it's exported automatically
        result = 0
        if operation == "add":
            result = a + b
        elif operation == "subtract":
            result = a - b

        self.history.append({
            "a": a,
            "b": b,
            "operation": operation,
            "result": result
        })

        return result

    def get_history(self) -> List[Dict[str, float]]:
        # No need to decorate this method, it's exported automatically
        return self.history

    def _internal_method(self) -> None:
        # This won't be exported because it starts with an underscore
        pass


# 2. Decorating individual methods (alternative approach)
# Only use this when you want to expose just specific methods of a class
class DataService:
    def __init__(self):
        self.data = {}

    @extensity
    def get_public_data(self) -> Dict:
        # Only this method will be exported
        return {"public": "data"}

    def internal_process(self) -> None:
        # This won't be exported
        pass


# 3. Decorating standalone functions
# This is the standard way to expose individual functions
@extensity
def add(a: float, b: float) -> float:
    return a + b

@extensity
def subtract(a: float, b: float) -> float:
    return a - b


# What NOT to do (redundant decorators)
@extensity  # This decorator is sufficient
class RedundantExample:

    # DO NOT do this - redundant decorator
    @extensity  # This decorator is redundant since the class is already decorated
    def redundant_method(self) -> str:
        return "This has a redundant decorator"