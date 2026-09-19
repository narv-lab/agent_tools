from core.exceptions import AgentToolError

class DiscoveryError(AgentToolError): pass

class DirectoryNotFoundError(DiscoveryError):
    def __init__(self, path: str):
        super().__init__(f"DirectoryNotFound: {path}")
        self.path = path

class PermissionDeniedError(DiscoveryError):
    def __init__(self, path: str):
        super().__init__(f"PermissionDenied: {path}")
        self.path = path

class InvalidPatternError(DiscoveryError):
    def __init__(self, pattern: str, reason: str):
        super().__init__(f"InvalidPattern: {pattern} ({reason})")
        self.pattern = pattern
        self.reason = reason

class EmptyQueryError(DiscoveryError):
    def __init__(self):
        super().__init__("EmptyQuery")

class IndexingFailedError(DiscoveryError):
    def __init__(self, reason: str):
        super().__init__(f"IndexingFailed: {reason}")
        self.reason = reason

class InvalidRegexError(DiscoveryError):
    def __init__(self, pattern: str, reason: str):
        super().__init__(f"InvalidRegex: {pattern} ({reason})")
        self.pattern = pattern
        self.reason = reason

class TooManyMatchesError(DiscoveryError):
    def __init__(self, count: int, limit: int):
        super().__init__(f"TooManyMatches: {count} matches found, limit is {limit}")
        self.count = count
        self.limit = limit

class FileNotFoundError(DiscoveryError):
    def __init__(self, path: str):
        super().__init__(f"FileNotFound: {path}")
        self.path = path

class InvalidRangeError(DiscoveryError):
    def __init__(self, reason: str):
        super().__init__(f"InvalidRange: {reason}")
        self.reason = reason

class SymbolNotFoundError(DiscoveryError):
    def __init__(self, symbol: str, file: str):
        super().__init__(f"SymbolNotFound: {symbol} in {file}")
        self.symbol = symbol
        self.file = file

class ParseError(DiscoveryError):
    def __init__(self, file: str, reason: str):
        super().__init__(f"ParseError: {file} ({reason})")
        self.file = file
        self.reason = reason

class CommandExecutionError(DiscoveryError):
    def __init__(self, reason: str):
        super().__init__(f"CommandExecutionError: {reason}")
        self.reason = reason

class FileReadError(DiscoveryError):
    def __init__(self, path: str, reason: str):
        super().__init__(f"FileReadError: {path} ({reason})")
        self.path = path
        self.reason = reason
