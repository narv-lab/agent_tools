"""
Common configuration constants and settings.
"""
import os

class Config:
    # Example config variables
    DEFAULT_TIMEOUT_MS = int(os.getenv("AGENT_TIMEOUT_MS", "30000"))
    LOG_LEVEL = os.getenv("AGENT_LOG_LEVEL", "INFO")
