import inspect
from typing import Any, Callable, Type, TypeVar, Union

from .core import registry

F = TypeVar('F', bound=Callable[..., Any])
C = TypeVar('C', bound=Type[Any])

def extensity(obj: Union[F, C]) -> Union[F, C]:
    """
    Decorator that marks Python objects for TypeScript export.

    This can be applied to:
    - Functions
    - Methods
    - Classes

    When applied to classes, all public methods and attributes are automatically exported.

    Example:
        @extensity
        def my_function(param: str) -> int:
            return len(param)

        @extensity
        class MyClass:
            def __init__(self, name: str):
                self.name = name
    """
    module_name = obj.__module__

    if inspect.isfunction(obj):
        # It's a function
        # Check if this is a method in a decorated class
        if hasattr(obj, '__qualname__'):
            class_name = obj.__qualname__.split('.')[0] if '.' in obj.__qualname__ else None
            if class_name:
                # Check if parent class is already decorated
                for reg_class_name, info in registry.classes.items():
                    if reg_class_name.endswith(class_name):
                        # Parent class is already decorated, don't register method separately
                        # Mark the method as decorated to avoid redundancy
                        setattr(obj, '_pyflow_decorated', True)
                        return obj

        # Register the function
        registry.register_function(obj, module_name)
        # Mark the function as decorated
        setattr(obj, '_pyflow_decorated', True)
        return obj

    elif inspect.isclass(obj):
        # It's a class
        # Register the class
        registry.register_class(obj, module_name)
        return obj

    else:
        raise TypeError(f"@extensity can only be applied to functions, methods, or classes, not {type(obj)}")