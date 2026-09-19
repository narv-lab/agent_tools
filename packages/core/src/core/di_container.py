"""
Simple Dependency Injection container.
"""
from typing import Dict, Any, Type, TypeVar, Callable

T = TypeVar('T')

class DIContainer:
    def __init__(self):
        self._services: Dict[Type, Any] = {}
        self._factories: Dict[Type, Callable[[], Any]] = {}

    def register(self, service_type: Type[T], instance: T):
        self._services[service_type] = instance

    def register_factory(self, service_type: Type[T], factory: Callable[[], T]):
        self._factories[service_type] = factory

    def resolve(self, service_type: Type[T]) -> T:
        if service_type in self._services:
            return self._services[service_type]
        if service_type in self._factories:
            instance = self._factories[service_type]()
            self._services[service_type] = instance
            return instance
        raise ValueError(f"Service {service_type} not registered")

# Global default container
container = DIContainer()
