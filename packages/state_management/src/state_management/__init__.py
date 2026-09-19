from typing import Dict, Any, Union
from .manager import StateManager
from .exceptions import (
    StateManagementError,
    NotAGitRepository,
    GitOperationFailed,
    CheckpointNotFound,
    UncommittedChangesExist
)

def snapshot_workspace() -> Union[str, Exception]:
    manager = StateManager()
    try:
        return manager.create_checkpoint()
    except Exception as e:
        return e

def restore_workspace(CommitHash: str) -> Dict[str, Any]:
    manager = StateManager()
    try:
        manager.revert_to_checkpoint(CommitHash)
        return {"success": True, "error_reason": None}
    except Exception as e:
        return {"success": False, "error_reason": str(e)}

__all__ = [
    "StateManager",
    "StateManagementError",
    "NotAGitRepository",
    "GitOperationFailed",
    "CheckpointNotFound",
    "UncommittedChangesExist",
    "snapshot_workspace",
    "restore_workspace"
]
