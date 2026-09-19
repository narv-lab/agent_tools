"""
Common error base classes and domain-specific errors.
L1_Structure dictates explicit error reporting without implicit fallbacks.
"""

class AgentToolError(Exception):
    """Base exception for all domain errors in the system."""
    pass

# System-level errors
class SystemCommandError(AgentToolError):
    """Raised when an underlying system command fails."""
    pass

class FileSystemError(AgentToolError):
    """Raised when there's an unexpected file system issue (e.g., permission denied)."""
    pass

class ConfigurationError(AgentToolError):
    """Raised when configuration is invalid."""
    pass
