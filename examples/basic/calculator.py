from pyflow import extensity
from typing import List, Dict, Any

@extensity
def add(a: float, b: float) -> float:
    """Add two numbers."""
    return a + b

@extensity
def subtract(a: float, b: float) -> float:
    """Subtract b from a."""
    return a - b

@extensity
def multiply(a: float, b: float) -> float:
    """Multiply two numbers."""
    return a * b

@extensity
def divide(a: float, b: float) -> float:
    """Divide a by b."""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b

@extensity
class Calculator:
    history: List[Dict[str, Any]] = []

    def calculate(self, a: float, b: float, operation: str) -> float:
        """Perform a calculation and store it in history."""
        result = 0

        if operation == "add":
            result = add(a, b)
        elif operation == "subtract":
            result = subtract(a, b)
        elif operation == "multiply":
            result = multiply(a, b)
        elif operation == "divide":
            result = divide(a, b)
        else:
            raise ValueError(f"Unknown operation: {operation}")

        # Store in history
        self.history.append({
            "a": a,
            "b": b,
            "operation": operation,
            "result": result
        })

        return result

    def get_history(self) -> List[Dict[str, Any]]:
        """Get calculation history."""
        return self.history

    def clear_history(self) -> None:
        """Clear calculation history."""
        self.history = []
