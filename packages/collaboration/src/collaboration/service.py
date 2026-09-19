import uuid
from typing import Dict, List
from collaboration.models import GuardedString, Error, SyncWorkspaceStateResult
from editing.models import FilePatch

class CollaborationService:
    def __init__(self):
        # In a real scenario, this state might be backed by a database or persistent storage
        self._async_requests: Dict[str, str] = {}

    def ask_human_sync(self, question: str) -> str:
        """
        Ask a question to a human synchronously and wait for the response.
        """
        print(f"Agent asks: {question}")
        return input("Your response: ")

    def ask_human_async(self, question: str) -> str:
        """
        Ask a question to a human asynchronously. Returns a request ID.
        """
        request_id = str(uuid.uuid4())
        self._async_requests[request_id] = "PENDING"
        # Asynchronously send question to human goes here
        return request_id

    def check_human_response(self, request_id: str) -> GuardedString:
        """
        Check the status of an asynchronous human request.
        """
        if request_id not in self._async_requests:
            return Error(message=f"Request ID not found: {request_id}")
        
        response = self._async_requests[request_id]
        return response

    def sync_workspace_state(self) -> SyncWorkspaceStateResult:
        """
        Sync the workspace state to detect any external changes (e.g., from a human).
        """

        # Use git status to detect uncommitted changes
        from execution.service import ExecutionService
        exec_svc = ExecutionService()
        res = exec_svc.execute_bash("git status --porcelain", timeout_ms=10000, profile=None, overrides={})
        external_changes = []
        if res.exit_code == 0 and res.stdout.strip():
            for line in res.stdout.strip().split("\n"):
                if len(line) > 3:
                    file_path = line[3:]
                    external_changes.append(FilePatch(file_path=file_path, intent="External manual change", patches=[]))
        return SyncWorkspaceStateResult(external_changes=external_changes)
