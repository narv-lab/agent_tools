from core.exceptions import AgentToolError

class StateManagementError(AgentToolError):
    """Base exception for state management module."""
    pass

class NotAGitRepository(StateManagementError):
    """Raised when the current directory is not a git repository."""
    pass

class GitOperationFailed(StateManagementError):
    """Raised when a Git operation fails."""
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Git operation failed: {reason}")

class CheckpointNotFound(StateManagementError):
    """Raised when the specified checkpoint ID does not exist."""
    def __init__(self, checkpoint_id: str):
        self.checkpoint_id = checkpoint_id
        super().__init__(f"Checkpoint not found: {checkpoint_id}")

class UncommittedChangesExist(StateManagementError):
    """Raised when uncommitted changes exist and force flag is not set."""
    pass
