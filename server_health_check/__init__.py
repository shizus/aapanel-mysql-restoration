"""Init file for server_health_check package."""
from .checker import ServerHealthCheck
from .main import main

__version__ = "0.1.0"
__all__ = ["ServerHealthCheck", "main"]
