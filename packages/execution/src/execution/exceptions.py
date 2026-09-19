from core.exceptions import AgentToolError

class ExecutionError(AgentToolError):
    pass

class InvalidProcessId(ExecutionError):
    def __init__(self, process_id: str):
        super().__init__(f"InvalidProcessId: {process_id}")
        self.process_id = process_id

class CommandExecutionFailed(ExecutionError):
    def __init__(self, reason: str):
        super().__init__(f"CommandExecutionFailed: {reason}")
        self.reason = reason
