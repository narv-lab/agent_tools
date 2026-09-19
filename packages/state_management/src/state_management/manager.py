
import datetime
import random
import string
from core.logger import get_logger
from state_management.exceptions import (
    NotAGitRepository,
    GitOperationFailed,
    CheckpointNotFound,
    UncommittedChangesExist
)

from execution.service import ExecutionService

logger = get_logger(__name__)

class _FakeResult:
    def __init__(self, returncode, stdout, stderr):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

def _run_git(cmd_list, capture_output=False, text=False):
    exec_svc = ExecutionService()
    cmd_str = " ".join([f'"{c}"' if " " in c and not c.startswith('--format=') else c for c in cmd_list])
    res = exec_svc.execute_bash(cmd_str, timeout_ms=30000, profile=None, overrides={})
    return _FakeResult(res.exit_code, res.stdout, res.stderr)

class StateManager:
    def create_checkpoint(self) -> str:
        """
        Saves the entire state of the current working directory as a Git commit and returns a unique CheckpointId.
        """
        try:
            res = _run_git(["git", "rev-parse", "--is-inside-work-tree"], capture_output=True, text=True)
            if res.returncode != 0:
                logger.error("CreateCheckpoint failed: NotAGitRepository")
                raise NotAGitRepository("Not a git repository")
        except FileNotFoundError:
            logger.error("CreateCheckpoint failed: GitOperationFailed (git executable not found)")
            raise GitOperationFailed("Git executable not found")

        # 1. Check if there are no commits yet
        res = _run_git(["git", "rev-list", "-n", "1", "--all"], capture_output=True, text=True)
        has_commits = res.returncode == 0 and res.stdout.strip() != ""

        if not has_commits:
            res = _run_git(["git", "commit", "--allow-empty", "-m", "Initial commit"], capture_output=True, text=True)
            if res.returncode != 0:
                logger.error(f"CreateCheckpoint failed (initial commit): GitOperationFailed - {res.stderr}")
                raise GitOperationFailed(res.stderr.strip() or "Failed to create initial commit")

        # 2. Add all changes to staging
        res = _run_git(["git", "add", "-A"], capture_output=True, text=True)
        if res.returncode != 0:
            logger.error(f"CreateCheckpoint failed (git add): GitOperationFailed - {res.stderr}")
            raise GitOperationFailed(res.stderr.strip() or "Failed to add files")

        # 3. Check for uncommitted changes
        res = _run_git(["git", "status", "--porcelain"], capture_output=True, text=True)
        has_changes = bool(res.stdout.strip())

        if not has_changes:
            res = _run_git(["git", "log", "-1", "--format=%s"], capture_output=True, text=True)
            if res.returncode != 0:
                logger.error(f"CreateCheckpoint failed (git log): GitOperationFailed - {res.stderr}")
                raise GitOperationFailed(res.stderr.strip() or "Failed to get HEAD commit message")
            
            head_msg = res.stdout.strip()
            if head_msg.startswith("checkpoint-"):
                logger.info(f"CreateCheckpoint: Returning existing CheckpointId {head_msg}")
                return head_msg
        
        # 4. Generate new CheckpointId
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        checkpoint_id = f"checkpoint-{timestamp}-{suffix}"

        # 5. Create commit
        commit_cmd = ["git", "commit"]
        if not has_changes:
            commit_cmd.append("--allow-empty")
        commit_cmd.extend(["-m", checkpoint_id])

        res = _run_git(commit_cmd, capture_output=True, text=True)
        if res.returncode != 0:
            logger.error(f"CreateCheckpoint failed (git commit): GitOperationFailed - {res.stderr}")
            raise GitOperationFailed(res.stderr.strip() or "Failed to create commit")

        logger.info(f"CreateCheckpoint: Created {checkpoint_id}")
        return checkpoint_id

    def revert_to_checkpoint(self, checkpoint_id: str, force: bool = False) -> bool:
        """
        Reverts the working directory to the state of the specified CheckpointId.
        """
        try:
            res = _run_git(["git", "rev-parse", "--is-inside-work-tree"], capture_output=True, text=True)
            if res.returncode != 0:
                logger.error("RevertToCheckpoint failed: NotAGitRepository")
                raise NotAGitRepository("Not a git repository")
        except FileNotFoundError:
            logger.error("RevertToCheckpoint failed: GitOperationFailed (git executable not found)")
            raise GitOperationFailed("Git executable not found")

        # 1. Validate checkpoint format roughly and check if exists
        res = _run_git(["git", "log", "--all", f"--grep=^{checkpoint_id}$", "--format=%H"], capture_output=True, text=True)
        if res.returncode != 0:
            logger.error(f"RevertToCheckpoint failed (git log): GitOperationFailed - {res.stderr}")
            raise GitOperationFailed(res.stderr.strip() or "Failed to search for checkpoint")
        
        commit_hashes = res.stdout.strip().split("\n")
        commit_hash = commit_hashes[0] if commit_hashes and commit_hashes[0] else None

        if not commit_hash:
            logger.error(f"RevertToCheckpoint failed: CheckpointNotFound - {checkpoint_id}")
            raise CheckpointNotFound(checkpoint_id)

        # 3. Check for uncommitted changes
        res = _run_git(["git", "status", "--porcelain"], capture_output=True, text=True)
        if res.returncode != 0:
            logger.error(f"RevertToCheckpoint failed (git status): GitOperationFailed - {res.stderr}")
            raise GitOperationFailed(res.stderr.strip() or "Failed to check status")
        
        has_changes = bool(res.stdout.strip())

        # 4. Check force flag
        if has_changes and not force:
            logger.error("RevertToCheckpoint failed: UncommittedChangesExist")
            raise UncommittedChangesExist("Uncommitted changes exist and force=False")

        # 5. Revert
        res = _run_git(["git", "reset", "--hard", commit_hash], capture_output=True, text=True)
        if res.returncode != 0:
            logger.error(f"RevertToCheckpoint failed (git reset): GitOperationFailed - {res.stderr}")
            raise GitOperationFailed(res.stderr.strip() or "Failed to reset")

        res = _run_git(["git", "clean", "-fd"], capture_output=True, text=True)
        if res.returncode != 0:
            logger.error(f"RevertToCheckpoint failed (git clean): GitOperationFailed - {res.stderr}")
            raise GitOperationFailed(res.stderr.strip() or "Failed to clean")

        logger.info(f"RevertToCheckpoint: Successfully reverted to {checkpoint_id}")
        return True
