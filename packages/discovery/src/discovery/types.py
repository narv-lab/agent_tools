from typing import TypedDict, List, Optional, Union, Any, Dict

SymbolURI = str
SymbolID = str
FilePath = str

class ErrorResult(TypedDict):
    error: str

GuardedString = Union[str, ErrorResult]

class GuardedListResult(TypedDict):
    results: List[Any]
    next_cursor: Optional[str]

GuardedList = Union[GuardedListResult, ErrorResult]

class PaginatedText(TypedDict):
    content: str
    is_truncated: bool
    next_line: Optional[int]

class Signature(TypedDict):
    name: str
    signature: str
    docstring: Optional[str]

ScopeInfo = List[Signature]

class Node(TypedDict):
    uri: SymbolURI
    type: str

class FileOverview(TypedDict):
    skeleton: str
    exports: List[SymbolURI]
    dependencies: List[FilePath]

class GrepMatch(TypedDict):
    file_path: str
    line_number: int
    snippet: str

class NodeTarget(TypedDict):
    node_uri: SymbolURI
    new_content: str
