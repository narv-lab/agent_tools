from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Union

@dataclass
class TestResult:
    test_name: str
    passed: bool
    message: str
    trace: Optional[List[str]] = None
    coverage: Optional[float] = None

@dataclass
class BashResult:
    stdout: str
    stderr: str
    exit_code: int

@dataclass
class SpawnResult:
    process_id: str

@dataclass
class ProcessOutput:
    log: str
    next_offset: int
    is_waiting_for_input: bool

@dataclass
class SuccessResult:
    success: bool
    error_reason: Optional[str] = None


@dataclass
class ErrorResult:
    """Typed representation of L1 Error(Message: String).
    Eliminates implicit failures and allows clients to identify errors in a consistent format.
    Serializes to JSON as {"error": "..."}.
    """
    error: str
