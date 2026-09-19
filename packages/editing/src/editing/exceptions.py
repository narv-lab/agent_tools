from core.exceptions import AgentToolError

class EditingError(AgentToolError):
    pass

class FileNotFound(EditingError):
    def __init__(self, path: str):
        super().__init__(f"FileNotFound: {path}")
        self.path = path

class PermissionDenied(EditingError):
    def __init__(self, path: str):
        super().__init__(f"PermissionDenied: {path}")
        self.path = path

class FileAlreadyExists(EditingError):
    def __init__(self, path: str):
        super().__init__(f"FileAlreadyExists: {path}")
        self.path = path

class InvalidPath(EditingError):
    def __init__(self, path: str, reason: str):
        super().__init__(f"InvalidPath: {path}, reason: {reason}")
        self.path = path
        self.reason = reason

class IsDirectory(EditingError):
    def __init__(self, path: str):
        super().__init__(f"IsDirectory: {path}")
        self.path = path
