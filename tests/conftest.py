import pytest
from core.di_container import container

@pytest.fixture(autouse=True)
def reset_di_container():
    """
    Resets the global DI container state before and after each test execution to maintain independence.
    """
    container._services.clear()
    container._factories.clear()
    yield
    container._services.clear()
    container._factories.clear()
