from dataclasses import dataclass
from typing import Union, List, Optional
from editing.models import FilePatch

@dataclass
class Error:
    message: str

GuardedString = Union[str, Error]

@dataclass
class SyncWorkspaceStateResult:
    external_changes: List[FilePatch]
